#!/usr/bin/env python3

import subprocess
import datetime
import argparse
import sys
import os

# Define cost per GPU-minute in different partitions
COST_PER_GPU_MINUTE = {
    "normal": 0.2,
    "large": 0.2,
    "buildlam": 0.2,
    # Add more GPU partitions as needed
}


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

        # Check if the user is a coordinator
        coord_check_cmd = ["sacctmgr", "show",
                           "account", account, "withcoord", "-n", "-P"]
        try:
            result = subprocess.run(
                coord_check_cmd, capture_output=True, text=True, check=True)
            accounts = result.stdout.strip().split('\n')
            for acc in accounts:
                acc_parts = acc.split('|')
                if len(acc_parts) >= 4 and acc_parts[0] == account and username in acc_parts[3].split(','):
                    # User is a coordinator, add -a option to show all members
                    cmd.extend(["-a"])
                    break
        except subprocess.CalledProcessError as e:
            print(f"Error checking coordinator status: {e}")

    if username and "-a" not in cmd:
        cmd.extend(["-u", username])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        print(f"Error running sacct command: {e}")
        print(f"Command output: {e.output}")
        return []


def get_gpu_limits(accounts, username=None):
    gpu_limits = {}
    for account in accounts:
        cmd = ["sshare", "-A", account, "-n", "-P",
               "-o", "Account,User,GrpTRESRaw,GrpTRESMins"]
        if username:
            cmd.extend(["-u", username])
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            if not lines:
                print(f"Warning: No output from sshare for account {account}")
                gpu_limits[account] = {"account": None}
                continue

            for line in lines:
                parts = line.split('|')
                if len(parts) >= 4:
                    acc, user, raw_limit, grp_tres_mins = parts[:4]
                    gpu_raw = next((item.split('=')[1] for item in raw_limit.split(
                        ',') if item.startswith('gres/gpu=')), None)
                    gpu_mins = next((item.split('=')[1] for item in grp_tres_mins.split(
                        ',') if item.startswith('gres/gpu=')), None)

                    gpu_limit = {"used": gpu_raw, "total": gpu_mins}

                    if user == '':  # This is the account-level line
                        gpu_limits[account] = {"account": gpu_limit}
                    else:
                        if account not in gpu_limits:
                            gpu_limits[account] = {}
                        gpu_limits[account][user] = gpu_limit
                else:
                    print(
                        f"Warning: Unexpected output format from sshare for account {account}")
                    print(f"Line: {line}")
                    gpu_limits[account] = {"account": None}
        except subprocess.CalledProcessError as e:
            print(f"Error running sshare command for account {account}: {e}")
            print(f"Command output: {e.output}")
            gpu_limits[account] = {"account": None}

    return gpu_limits


def parse_time(time_str_in_second):
    time_str_in_second = int(time_str_in_second)
    return time_str_in_second / 60


def calculate_cost(usage_data):
    usage_by_user = {}
    all_accounts = set()

    for job in usage_data:
        if not job:
            continue
        job_parts = job.split('|')
        if len(job_parts) < 6:
            continue
        job_id, user, elapsed, alloc_tres, partition, account = job_parts

        if not user or not partition or partition not in COST_PER_GPU_MINUTE:
            continue

        minutes = parse_time(elapsed)
        gpus = next((int(item.split('=')[1]) for item in alloc_tres.split(
            ',') if item.startswith('gres/gpu=')), 0)

        if gpus == 0:
            continue  # Skip jobs without GPU usage

        if user not in usage_by_user:
            usage_by_user[user] = {"total": 0,
                                   "partitions": {}, "accounts": set()}

        if partition not in usage_by_user[user]["partitions"]:
            usage_by_user[user]["partitions"][partition] = {
                "gpu_minutes": 0, "cost": 0}

        usage_by_user[user]["partitions"][partition]["gpu_minutes"] += minutes * gpus
        usage_by_user[user]["accounts"].add(account)
        all_accounts.add(account)

        gpu_cost_per_minute = COST_PER_GPU_MINUTE[partition]
        job_cost = minutes * gpus * gpu_cost_per_minute
        usage_by_user[user]["total"] += job_cost
        usage_by_user[user]["partitions"][partition]["cost"] += job_cost

    return usage_by_user, all_accounts


def format_output(usage_by_user, total_cost, gpu_limits):
    # Table header
    header = ""
    header += "┌──────────────┬──────────────┬────────────────────────────────────────────────┬────────────┬──────────────┐\n"
    header += "│     User     │    Account   │ Partition Details                              │ Total Cost │ GPU Limit    │\n"
    header += "├──────────────┼──────────────┼────────────────────────────────────────────────┼────────────┼──────────────┤\n"

    # Table body
    body = ""
    for user, data in usage_by_user.items():
        # Assume one account per user for simplicity
        account = next(iter(data["accounts"]))
        partition_details = ""
        partition_details += "┌───────────┬───────────────┬──────────────┐\n"
        partition_details += "│ Partition │  GPU Minutes  │     Cost     │\n"
        partition_details += "├───────────┼───────────────┼──────────────┤\n"

        for partition, usage in data["partitions"].items():
            partition_details += f"│ {partition:<9} │ {usage['gpu_minutes']:>13.0f} │ ${usage['cost']:>11.2f} │\n"

        partition_details += "└───────────┴───────────────┴──────────────┘"

        # Split partition details into lines
        partition_lines = partition_details.split('\n')

        # Get GPU limit for the user
        gpu_limit = "N/A"
        if account in gpu_limits and user in gpu_limits[account]:
            user_limit = gpu_limits[account][user]
            if user_limit["total"] is not None:
                used_minutes = float(
                    user_limit["used"]) if user_limit["used"] else 0
                total_minutes = float(
                    user_limit["total"]) if user_limit["total"] else 0
                gpu_limit = f"{used_minutes:.0f}/{total_minutes:.0f}"

        # First line with user, account, first line of partition details, total cost, and GPU limit
        body += f"│ {user:<12} │ {account:<12} │ {partition_lines[0]:<46} │ ${data['total']:>9.2f} │ {gpu_limit:<12} │\n"

        # Remaining lines of partition details
        for line in partition_lines[1:]:
            body += f"│              │              │ {line:<46} │            │              │\n"

        if user != list(usage_by_user.keys())[-1]:
            body += f"├──────────────┼──────────────┼────────────────────────────────────────────────┼────────────┼──────────────┤\n"
        else:
            body += f"├──────────────┴──────────────┴────────────────────────────────────────────────┼────────────┼──────────────┤\n"

    # Table footer
    footer = f"│ Total                                                                        │ ${total_cost:>9.2f} │              │\n"
    footer += "└──────────────────────────────────────────────────────────────────────────────┴────────────┴──────────────┘"

    return header + body + footer


def main():
    print("")
    parser = argparse.ArgumentParser(
        description="Calculate Slurm GPU usage and cost")
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
        elif not args.username and args.account:
            # Check all users in the account
            print(
                "Warning: Running as root and no user specified. All users in the account will be checked.")
            args.username = None

    end_date = datetime.date.fromisoformat(args.end)
    current_date = datetime.date.today()

    if end_date == current_date:
        print("Warning: Report includes today's date. Some very recent jobs may not be included due to accounting delays.")
        print("For most accurate results, wait a few minutes and run the report again.")

    end_date_with_buffer = (datetime.datetime.combine(
        end_date, datetime.time.max) + datetime.timedelta(minutes=15)).date()

    usage_data = get_usage(
        args.start, end_date_with_buffer.isoformat(), args.account, args.username)
    usage_by_user, all_accounts = calculate_cost(usage_data)

    if not usage_by_user:
        print(f"No GPU usage data found for the specified criteria.")
        sys.exit(0)

    gpu_limits = get_gpu_limits(all_accounts, args.username)

    total_cost = sum(data['total'] for data in usage_by_user.values())

    print(f"\nGPU Usage report from {args.start} to {args.end}")
    print(format_output(usage_by_user, total_cost, gpu_limits))

    # Print account-level GPU limits information
    print("\nAccount-level GPU Limits:")
    for account in all_accounts:
        account_limit = gpu_limits.get(account, {}).get("account")
        if account_limit and account_limit["total"] is not None:
            used_minutes = float(
                account_limit["used"]) if account_limit["used"] else 0
            total_minutes = float(
                account_limit["total"]) if account_limit["total"] else 0
            print(
                f"  Account {account}: Used: {used_minutes:.0f}, Total: {total_minutes:.0f}")
        else:
            print(f"  Account {account}: N/A")
    print("")


if __name__ == "__main__":
    main()
