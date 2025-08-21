from collections import defaultdict
from typing import List, Dict, Any, Set
from .utils import parse_tres, parse_time

def initialize_usage(associations: List[Dict[str, str]], partitions: List[str]) -> (Dict, Dict):
    """Initializes the nested dictionary for usage data using defaultdict."""
    # Structure: {account: {users: {user: {partitions: {}, limits: {}}}}}
    usage_by_account = defaultdict(lambda: {'users': defaultdict(lambda: {'partitions': defaultdict(lambda: {'hours': 0.0}), 'limits': {}})})
    account_limits = defaultdict(dict)

    for assoc in associations:
        account = assoc['account']
        user = assoc['user']
        partition = assoc['partition']
        tres = parse_tres(assoc['tres_mins'])

        if not user:  # Account-level limits
            if 'gres/gpu' in tres:
                for part in partitions:
                    account_limits[account][part] = tres.get('gres/gpu', 0) / 60
            continue

        if partition and partition in partitions:
            usage_by_account[account]['users'][user]['limits'][partition] = {
                'gpu_limit': tres.get('gres/gpu', 0) / 60,
                'cpu_limit': tres.get('cpu', 0) / 60
            }
            
    return usage_by_account, account_limits

def accumulate_usage(usage_data: List[str], usage_by_account: Dict, partitions: List[str], associations: List[Dict], runaway_jobs: Set[str]) -> Dict:
    """Accumulates usage data, filtering out runaway jobs."""
    for job_line in usage_data:
        if not job_line:
            continue
        job_parts = job_line.split('|')
        if len(job_parts) < 6:
            continue

        job_id, user, elapsed, alloc_tres, partition, account = job_parts
        
        if job_id in runaway_jobs:
            continue
            
        if not all([partition, account, user]) or partition not in partitions:
            continue

        hours = parse_time(elapsed)
        gpus = next((int(item.split('=')[1]) for item in alloc_tres.split(',') if item.startswith('gres/gpu=')), 0)
        cpus = next((int(item.split('=')[1]) for item in alloc_tres.split(',') if item.startswith('cpu=')), 1)
        resource_hours = hours * gpus if gpus > 0 else hours * cpus

        user_entry = usage_by_account[account]['users'][user]
        user_entry['partitions'][partition]['hours'] += resource_hours

    # Ensure every user has an entry for each of their allowed partitions
    for assoc in associations:
        if assoc['user'] and assoc['partition']:
            account, user, partition = assoc['account'], assoc['user'], assoc['partition']
            if user in usage_by_account.get(account, {}).get('users', {}):
                # This will create the partition with 0.0 hours if it doesn't exist
                _ = usage_by_account[account]['users'][user]['partitions'][partition]

    return usage_by_account


def calculate_usage(usage_data: List[str], associations: List[Dict], partitions: List[str], runaway_jobs: Set[str]) -> (Dict, Dict):
    """The main calculation function."""
    usage_by_account, account_limits = initialize_usage(associations, partitions)
    usage_by_account = accumulate_usage(usage_data, usage_by_account, partitions, associations, runaway_jobs)
    return usage_by_account, account_limits