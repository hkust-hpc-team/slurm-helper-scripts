import subprocess
import sys
from typing import List, Dict, Any, Set

def _run_command(cmd: List[str]) -> str:
    """Helper function to run a command and handle errors."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, encoding='utf-8'
        )
        return result.stdout.strip()
    except FileNotFoundError:
        print(f"Error: Command '{cmd[0]}' not found. Is Slurm installed and in your PATH?", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(cmd)}\n{e.stderr}", file=sys.stderr)
        return ""

def get_available_partitions() -> List[str]:
    """Get a list of all available partition names."""
    output = _run_command(["sinfo", "--noheader", "-o", "%P"])
    return output.split('\n') if output else []

def get_association_data(account: str = None, user: str = None) -> List[Dict[str, str]]:
    """Get association data from sacctmgr."""
    avail_partitions = ",".join(get_available_partitions())
    if not avail_partitions:
        return []
    
    cmd = [
        "sacctmgr", "show", "association", f"partition={avail_partitions}",
        "--parsable", "--noheader", "format=Account,User,Partition,GrpTRESMins", "--readonly"
    ]
    if account:
        cmd.append(f"account={account}")
    if user:
        cmd.append(f"user={user}")
        
    output = _run_command(cmd)
    associations = []
    if not output:
        return []
        
    for line in output.split('\n'):
        if line:
            parts = line.split('|')
            if len(parts) >= 4:
                associations.append({
                    'account': parts[0],
                    'user': parts[1],
                    'partition': parts[2],
                    'tres_mins': parts[3]
                })
    return associations

def get_usage_data(start_date: str, end_date: str, account: str = None, username: str = None) -> List[str]:
    """Get raw usage data from sacct."""
    cmd = [
        "sacct", "-n", "-P", "-X",
        "-S", start_date,
        "-E", end_date,
        "--format=JobID,User,ElapsedRaw,AllocTRES,Partition,Account",
        "--truncate", "--allusers",
    ]
    if account:
        cmd.extend(["-A", account])
    if username:
        cmd.extend(["-u", username])
        
    output = _run_command(cmd)
    return output.split('\n') if output else []

def get_runaway_jobs() -> Set[str]:
    """Get a set of runaway job IDs (in sacct as RUNNING, but not in squeue)."""
    sacct_output = _run_command(
        ['sacct', '--allusers', '-X', '-n', '--format=jobid', '--state=RUNNING']
    )
    all_jobs = {job.strip() for job in sacct_output.splitlines() if job.strip()}

    squeue_output = _run_command(
        ['squeue', '--noheader', '-h', '-o', '%i']
    )
    running_jobs = {job.strip() for job in squeue_output.splitlines() if job.strip()}
    
    runaway = all_jobs - running_jobs
    if runaway:
        print(f"Info: Found and excluded {len(runaway)} runaway jobs.", file=sys.stderr)
    return runaway