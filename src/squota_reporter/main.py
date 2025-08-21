import argparse
import datetime
import os
import sys
from .slurm_client import get_available_partitions, get_association_data, get_usage_data, get_runaway_jobs
from .usage_calculator import calculate_usage
from .report_renderer import render_report
from .utils import get_cluster

RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def run():
    parser = argparse.ArgumentParser(
        description="Show Slurm usage by partition and account")
    parser.add_argument("-u", "--username", help="Username to check usage for (optional)", default=None)
    parser.add_argument("-S", "--start", help="Start date (YYYY-MM-DD)", default=(datetime.date.today().replace(day=1)).isoformat())
    parser.add_argument("-E", "--end", help="End date (YYYY-MM-DD)", default=datetime.date.today().isoformat())
    parser.add_argument("-A", "--account", help="Specific account to check (optional)")
    parser.add_argument("--no-runaway-filter", action="store_true", help="Disable the runaway job filter")
    args = parser.parse_args()

    current_user = os.getenv('USER')
    if current_user == 'root' and not (args.username or args.account):
        print("Error: As root, you must specify either a username or an account.", file=sys.stderr)
        sys.exit(1)

    end_date = datetime.date.fromisoformat(args.end)
    end_date_with_buffer = (datetime.datetime.combine(end_date, datetime.time.max) + datetime.timedelta(minutes=15)).date()

    runaway_jobs = get_runaway_jobs() if not args.no_runaway_filter else set()

    partitions = get_available_partitions()
    associations = get_association_data(args.account, args.username)
    usage_data = get_usage_data(args.start, end_date_with_buffer.isoformat(), args.account, args.username)
    
    usage_by_account, account_limits = calculate_usage(
        usage_data, associations, partitions, runaway_jobs
    )

    if not usage_by_account:
        print(f"{RED}No usage data found for the specified criteria.{RESET}")
        sys.exit(0)

    title = f"\n{GREEN}Usage report from {BLUE}{args.start}{GREEN} to {BLUE}{args.end}{RESET}"
    print(render_report(usage_by_account, account_limits, title))

    cluster = get_cluster()
    if cluster == 'superpod':
        print(f'{YELLOW}Note: "Hours" refers to {RED}GPU-hour{YELLOW} for GPU partitions and {RED}CPU-core-hour{YELLOW} for CPU partitions.\nTo convert {RED}GPU-hour{YELLOW} to {RED}GPU-node-hour{YELLOW}, divide {RED}GPU-hour{YELLOW} by 8.{RESET}')
    else:
        print(f'{YELLOW}Note: "Hours" refers to {RED}GPU-hour{YELLOW} for GPU partitions and {RED}CPU-core-hour{YELLOW} for CPU partitions.{RESET}')

if __name__ == "__main__":
    run()