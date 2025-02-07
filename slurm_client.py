#!/usr/bin/env python3
import subprocess


def get_available_partitions():
    cmd = ["sinfo", "--noheader", "--format=%P"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        print(f"Error getting partitions: {e}")
        return []


def get_association_data(account=None, user=None):
    avail_partitions = ",".join(get_available_partitions())
    cmd = [
        "sacctmgr", "show", "association", f"partition={avail_partitions}", "--parsable", "--noheader",
        "format=Account,User,Partition,GrpTRESMins", "--readonly"
    ]
    if account:
        cmd.append(f"account={account}")
    if user:
        cmd.append(f"user={user}")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True)
        associations = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                associations.append({
                    'account': parts[0],
                    'user': parts[1],
                    'partition': parts[2],
                    'tres_mins': parts[3]
                })
        return associations
    except subprocess.CalledProcessError as e:
        print(f"Error getting association data: {e}")
        return []


def get_usage_data(start_date, end_date, account=None, username=None):
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
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        print(f"Error running sacct command: {e}")
        return []
