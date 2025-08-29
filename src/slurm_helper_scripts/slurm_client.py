import subprocess
import sys
from typing import List, Dict, Set, Optional

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

def get_association_data(
    account: Optional[str] = None,
    users: Optional[List[str]] = None,
    partitions: Optional[List[str]] = None
) -> List[Dict[str, str]]:
    """
    Get association data from sacctmgr.

    - If 'partitions' is provided, use it directly (even if not visible via sinfo).
    - Otherwise, use visible partitions from sinfo.
    - Results are filtered by 'users' (if provided) in Python, to avoid sacctmgr's AND semantics.
    """
    if partitions is None:
        avail_partitions = ",".join(get_available_partitions())
        if not avail_partitions:
            return []
    else:
        avail_partitions = ",".join(partitions)

    cmd = ["sacctmgr", "show", "association"]
    if avail_partitions:
        cmd.append(f"partition={avail_partitions}")
    cmd += ["--parsable", "--noheader", "format=Account,User,Partition,GrpTRESMins", "--readonly"]
    if account:
        cmd.append(f"account={account}")
    # We intentionally do NOT add user=... here; we will filter after fetching.

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

    if users:
        users_set = set(users)
        # Keep account-level limits (user == "") and the selected users
        associations = [a for a in associations if (a['user'] in users_set) or (a['user'] == "")]
    return associations

def get_usage_data(
    start_date: str,
    end_date: str,
    account: Optional[str] = None,
    users: Optional[List[str]] = None
) -> List[str]:
    """Get raw usage data from sacct.

    If 'users' is provided, it's joined via comma and passed to '-u'.
    """
    cmd = [
        "sacct", "-n", "-P", "-X",
        "-S", start_date,
        "-E", end_date,
        "--format=JobID,User,ElapsedRaw,AllocTRES,Partition,Account",
        "--truncate", "--allusers",
    ]
    if account:
        cmd.extend(["-A", account])
    if users:
        cmd.extend(["-u", ",".join(users)])

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