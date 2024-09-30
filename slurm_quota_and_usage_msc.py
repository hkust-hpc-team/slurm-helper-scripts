#!/usr/bin/env python3

import subprocess
import datetime
import argparse
import sys
import os


def get_usage(start_date, end_date, account=None, username=None):
    cmd = [
        "sacct", "-n", "-P", "-X",
        "-S", start_date,
        "-E", end_date,
        "--format=JobID,User,ElapsedRaw,AllocTRES,Partition,Account",
        "--qos=normal_qos,large_qos",
        "--truncate"
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
        print(f"Command output: {e.output}")
        return []


def get_gpu_limits(accounts):
    gpu_limits = {}
    for account in accounts:
        cmd = ["sshare", "-A", account, "-n",
               "-P", "-o", "Account,GrpTRESMins"]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            if not lines:
                print(f"Warning: No output from sshare for account {account}")
                gpu_limits[account] = None
                continue

            for line in lines:
                parts = line.split('|')
                if len(parts) >= 2:
                    acc, grp_tres_mins = parts[:2]
                    gpu_mins = next((item.split('=')[1] for item in grp_tres_mins.split(
                        ',') if item.startswith('gres/gpu=')), None)

                    gpu_limits[account] = float(
                        gpu_mins) / 60 if gpu_mins else None
                else:
                    print(
                        f"Warning: Unexpected output format from sshare for account {account}")
                    print(f"Line: {line}")
                    gpu_limits[account] = None
        except subprocess.CalledProcessError as e:
            print(f"Error running sshare command for account {account}: {e}")
            print(f"Command output: {e.output}")
            gpu_limits[account] = None

    return gpu_limits


def parse_time(time_str_in_second):
    time_str_in_second = int(time_str_in_second)
    return time_str_in_second / 3600  # Convert to hours


def calculate_gpu_hours(usage_data):
    usage_by_account = {}
    all_accounts = set()

    for job in usage_data:
        if not job:
            continue
        job_parts = job.split('|')
        if len(job_parts) < 6:
            continue
        job_id, user, elapsed, alloc_tres, partition, account = job_parts

        if not partition or not account:
            continue

        hours = parse_time(elapsed)
        gpus = next((int(item.split('=')[1]) for item in alloc_tres.split(
            ',') if item.startswith('gres/gpu=')), 0)

        if gpus == 0:
            continue  # Skip jobs without GPU usage

        if account not in usage_by_account:
            usage_by_account[account] = {"total": 0, "partitions": {}}

        if partition not in usage_by_account[account]["partitions"]:
            usage_by_account[account]["partitions"][partition] = {
                "gpu_hours": 0}

        gpu_hours = hours * gpus
        usage_by_account[account]["partitions"][partition]["gpu_hours"] += gpu_hours
        all_accounts.add(account)

        usage_by_account[account]["total"] += gpu_hours

    return usage_by_account, all_accounts


def format_output(usage_by_account, gpu_limits):
    header = "┌────────────────┬─────────────────────────────────┬──────────────────────┐\n"
    header += "│    Account     │        Partition Details        │  Usage (GPU Hours)   │\n"
    header += "├────────────────┼─────────────────────────────────┼──────────────────────┤\n"

    body = ""
    for account, data in usage_by_account.items():
        partition_details = "┌───────────┬───────────────┐\n"
        partition_details += "│ Partition │   GPU Hours   │\n"
        partition_details += "├───────────┼───────────────┤\n"

        for partition, usage in data["partitions"].items():
            partition_details += f"│ {partition:<9} │ {usage['gpu_hours']:>13.2f} │\n"

        partition_details += "└───────────┴───────────────┘"

        partition_lines = partition_details.split('\n')

        gpu_limit = gpu_limits.get(account, None)
        usage_str = f"{data['total']:.2f} / {gpu_limit:.2f}" if gpu_limit is not None else f"{data['total']:.2f} / n/a"

        body += f"│ {account:<14} │ {partition_lines[0]:<31} │ {usage_str:>20} │\n"

        for line in partition_lines[1:]:
            body += f"│                │ {line:<31} │                      │\n"

        if account != list(usage_by_account.keys())[-1]:
            body += f"├────────────────┼─────────────────────────────────┼──────────────────────┤\n"
        else:
            body += f"└────────────────┴─────────────────────────────────┴──────────────────────┘\n"

    return header + body


def main():
    print("")
    parser = argparse.ArgumentParser(description="Calculate Slurm GPU usage")
    parser.add_argument(
        "-u", "--username", help="Username to check usage for (optional)", default=None)
    parser.add_argument("-S", "--start", help="Start date (YYYY-MM-DD)",
                        default=(datetime.date.today().replace(day=1)).isoformat())
    parser.add_argument("-E", "--end", help="End date (YYYY-MM-DD)",
                        default=datetime.date.today().isoformat())
    parser.add_argument("-A", "--account",
                        help="Specific account to check (optional)")

    args = parser.parse_args()

    current_user = os.getenv('USER')

    if current_user != 'root':
        if args.username and args.username != current_user:
            print(
                f"Error: You don't have permission to view {args.username}'s usage.")
            sys.exit(1)
        args.username = current_user
        print(f"Using current user: {current_user}")
    else:
        if not args.username and not args.account:
            print("Error: As root, you must specify either a username or an account.")
            sys.exit(1)

    end_date = datetime.date.fromisoformat(args.end)
    current_date = datetime.date.today()

    if end_date == current_date:
        print("Warning: Report includes today's date. Some very recent jobs may not be included due to accounting delays.")
        print("For most accurate results, wait a few minutes and run the report again.")

    end_date_with_buffer = (datetime.datetime.combine(
        end_date, datetime.time.max) + datetime.timedelta(minutes=15)).date()

    usage_data = get_usage(
        args.start, end_date_with_buffer.isoformat(), args.account, args.username)
    usage_by_account, all_accounts = calculate_gpu_hours(usage_data)

    if not usage_by_account:
        print(f"No GPU usage data found for the specified criteria.")
        sys.exit(0)

    gpu_limits = get_gpu_limits(all_accounts)

    print(f"\nGPU Usage report from {args.start} to {args.end}")
    print(format_output(usage_by_account, gpu_limits))

    print("")


if __name__ == "__main__":
    main()
