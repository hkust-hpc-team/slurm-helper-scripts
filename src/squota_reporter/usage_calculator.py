from utils import parse_tres, parse_time


def initialize_usage(associations, partitions):
    usage_by_account = {}
    account_limits = {}

    for assoc in associations:
        account = assoc['account']
        user = assoc['user'] if assoc['user'] else None
        partition = assoc['partition'] if assoc['partition'] else None
        tres = parse_tres(assoc['tres_mins'])

        if not user:
            # Account-level limits if no user is defined.
            for part in partitions:
                if 'gres/gpu' in tres:
                    account_limits.setdefault(account, {})[
                        part] = tres.get('gres/gpu', 0) / 60
            continue

        if account not in usage_by_account:
            usage_by_account[account] = {'users': {}}
        if user not in usage_by_account[account]['users']:
            usage_by_account[account]['users'][user] = {
                'partitions': {}, 'limits': {}}
        if partition and partition in partitions:
            usage_by_account[account]['users'][user]['limits'][partition] = {
                'gpu_limit': tres.get('gres/gpu', 0) / 60,
                'cpu_limit': tres.get('cpu', 0) / 60
            }
    return usage_by_account, account_limits


def accumulate_usage(usage_data, usage_by_account, partitions, associations):
    for job in usage_data:
        if not job:
            continue
        job_parts = job.split('|')
        if len(job_parts) < 6:
            continue

        _, user, elapsed, alloc_tres, partition, account = job_parts
        if not partition or not account or not user or partition not in partitions:
            continue

        if account not in usage_by_account:
            usage_by_account[account] = {'users': {}}
        if user not in usage_by_account[account]['users']:
            usage_by_account[account]['users'][user] = {
                'partitions': {}, 'limits': {}}

        hours = parse_time(elapsed)
        # Extract gres/gpu and cpu counts
        gpus = next((int(item.split('=')[1]) for item in alloc_tres.split(',')
                     if item.startswith('gres/gpu=')), 0)
        cpus = next((int(item.split('=')[1]) for item in alloc_tres.split(',')
                     if item.startswith('cpu=')), 1)
        resource_hours = hours * gpus if gpus > 0 else hours * cpus

        user_entry = usage_by_account[account]['users'][user]
        if partition not in user_entry['partitions']:
            user_entry['partitions'][partition] = {'hours': 0.0}
        user_entry['partitions'][partition]['hours'] += resource_hours

    # Ensure every user has an entry for each allowed partition.
    for account, account_data in usage_by_account.items():
        for user, user_data in account_data['users'].items():
            allowed_partitions = [
                assoc['partition'] for assoc in associations
                if assoc['account'] == account and assoc['user'] == user and assoc['partition']
            ]
            for partition in allowed_partitions:
                if partition not in user_data['partitions']:
                    user_data['partitions'][partition] = {'hours': 0.0}

    return usage_by_account


def calculate_usage(usage_data, associations, partitions):
    usage_by_account, account_limits = initialize_usage(
        associations, partitions)
    usage_by_account = accumulate_usage(
        usage_data, usage_by_account, partitions, associations)
    return usage_by_account, account_limits
