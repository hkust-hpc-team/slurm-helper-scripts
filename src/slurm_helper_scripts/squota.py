import argparse
import datetime
import os
import sys
from typing import List, Optional, Iterable

from .slurm_client import (
    get_available_partitions,
    get_association_data,
    get_usage_data,
    get_runaway_jobs,
)
from .usage_calculator import calculate_usage
from .report_renderer import render_report
from .utils import get_cluster

RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def _normalize_partitions(parts: Iterable[str]) -> List[str]:
    """Normalize partition names: split by comma, strip spaces, drop trailing '*' and dedup (preserve order)."""
    seen = set()
    result: List[str] = []
    for raw in parts:
        if not raw:
            continue
        for p in str(raw).split(","):
            name = p.strip().rstrip("*")
            if name and name not in seen:
                seen.add(name)
                result.append(name)
    return result


def _normalize_users(users_in: Optional[Iterable[str]]) -> Optional[List[str]]:
    """Split on comma, strip spaces, dedup (preserve order). Return None if no users."""
    if not users_in:
        return None
    seen = set()
    users: List[str] = []
    for raw in users_in:
        if not raw:
            continue
        for u in str(raw).split(","):
            name = u.strip()
            if name and name not in seen:
                seen.add(name)
                users.append(name)
    return users if users else None


def _csv_level1(usage_by_account, partitions: List[str]) -> str:
    """
    Level 1 CSV: Account-level totals per partition.
    Header: Account,<partition1>,<partition2>,...
    """
    cols = ["Account"] + partitions
    lines = [",".join(cols)]
    for account in sorted(usage_by_account.keys()):
        # Sum over all users for each partition
        part_totals = {p: 0.0 for p in partitions}
        for user_data in usage_by_account[account]["users"].values():
            for p in partitions:
                hours = user_data["partitions"].get(p, {"hours": 0.0})["hours"]
                part_totals[p] += hours
        row = [account] + [f"{part_totals[p]:.2f}" for p in partitions]
        lines.append(",".join(row))
    return "\n".join(lines)


def _csv_level2(usage_by_account, partitions: List[str]) -> str:
    """
    Level 2 CSV: Account,User per-partition usage.
    Header: Account,User,<partition1>,<partition2>,...
    """
    cols = ["Account", "User"] + partitions
    lines = [",".join(cols)]
    for account in sorted(usage_by_account.keys()):
        users = usage_by_account[account]["users"]
        for user in sorted(users.keys()):
            udata = users[user]
            row_vals = []
            for p in partitions:
                hours = udata["partitions"].get(p, {"hours": 0.0})["hours"]
                row_vals.append(f"{hours:.2f}")
            lines.append(",".join([account, user] + row_vals))
    return "\n".join(lines)


def run():
    parser = argparse.ArgumentParser(
        description="Show Slurm usage by partition and account"
    )
    # Multi-user (alias --username kept for backward compatibility)
    parser.add_argument(
        "-u",
        "--user",
        "--username",
        dest="users",
        action="append",
        help="Specify user(s). Can be repeated or comma-separated (e.g., -u alice -u bob or -u alice,bob)",
        default=None,
    )
    parser.add_argument(
        "-p",
        "--partition",
        dest="partitions",
        action="append",
        help="Specify partition(s). Can be repeated or comma-separated. If omitted, only visible partitions are used.",
        default=None,
    )
    parser.add_argument(
        "-S",
        "--start",
        help="Start date (YYYY-MM-DD)",
        default=(datetime.date.today().replace(day=1)).isoformat(),
    )
    parser.add_argument(
        "-E",
        "--end",
        help="End date (YYYY-MM-DD)",
        default=datetime.date.today().isoformat(),
    )
    parser.add_argument("-A", "--account", help="Specific account to check (optional)")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all usage from the beginning (overrides --start to 1970-01-01)",
    )
    parser.add_argument(
        "--no-runaway-filter",
        action="store_true",
        help="Disable the runaway job filter",
    )
    parser.add_argument(
        "--csv",
        nargs="?",
        const="lv1",
        choices=["lv1", "lv2"],
        help="Output CSV for a single level: lv1 (account-partition) or lv2 (account-user-partition). "
        "If provided without a value, defaults to lv1.",
    )
    args = parser.parse_args()

    # Handle --all flag: override start date to beginning of time
    default_start = datetime.date.today().replace(day=1).isoformat()
    if args.all:
        if args.start != default_start:
            print(
                f"{YELLOW}Warning: --all overrides --start; using 1970-01-01{RESET}",
                file=sys.stderr,
            )
        start_date = "1970-01-01"
    else:
        start_date = args.start

    # Normalize users and partitions
    users = _normalize_users(args.users)
    if args.partitions:
        partitions = _normalize_partitions(args.partitions)
    else:
        # Default: only visible partitions (normalize to drop trailing '*')
        partitions = _normalize_partitions(get_available_partitions())

    current_user = os.getenv("USER")
    if current_user == "root" and not (users or args.account):
        print(
            "Error: As root, you must specify either a user (--user) or an account (--account).",
            file=sys.stderr,
        )
        sys.exit(1)

    # Extend end date by 15 minutes buffer (cross-midnight jobs)
    end_date = datetime.date.fromisoformat(args.end)
    end_date_with_buffer = (
        datetime.datetime.combine(end_date, datetime.time.max)
        + datetime.timedelta(minutes=15)
    ).date()

    runaway_jobs = get_runaway_jobs() if not args.no_runaway_filter else set()

    # sacctmgr associations: if user(s) specified, fetch all and filter by user in Python (handled inside function)
    associations = get_association_data(
        args.account, users=users, partitions=partitions
    )
    usage_data = get_usage_data(
        start_date, end_date_with_buffer.isoformat(), args.account, users
    )

    usage_by_account, account_limits = calculate_usage(
        usage_data, associations, partitions, runaway_jobs
    )

    # CSV path (single level only)
    if args.csv is not None:
        level = args.csv  # lv1 or lv2
        if level == "lv1":
            print(_csv_level1(usage_by_account, partitions))
        else:
            print(_csv_level2(usage_by_account, partitions))
        return

    # Human-readable table path
    if not usage_by_account:
        print(f"{RED}No usage data found for the specified criteria.{RESET}")
        sys.exit(0)

    title = f"\n{GREEN}Usage report from {BLUE}{start_date}{GREEN} to {BLUE}{args.end}{RESET}"
    print(render_report(usage_by_account, account_limits, title))

    cluster = get_cluster()
    if cluster == "superpod":
        print(
            f'{YELLOW}Note: "Hours" refers to {RED}GPU-hour{YELLOW} for GPU partitions and {RED}CPU-core-hour{YELLOW} for CPU partitions.\nTo convert {RED}GPU-hour{YELLOW} to {RED}GPU-node-hour{YELLOW}, divide {RED}GPU-hour{YELLOW} by 8.{RESET}'
        )
    else:
        print(
            f'{YELLOW}Note: "Hours" refers to {RED}GPU-hour{YELLOW} for GPU partitions and {RED}CPU-core-hour{YELLOW} for CPU partitions.{RESET}'
        )
