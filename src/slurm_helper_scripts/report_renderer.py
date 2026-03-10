from .table import Table


def render_report(usage_by_account, account_limits, title):
    table = Table(title=title)
    table.add_column("Account", alignment="left")
    table.add_column("Account Total (Hours)", alignment="right")
    table.add_column("Details", alignment="left")

    for account, account_data in usage_by_account.items():
        # Calculate per-partition totals for the account
        account_partition_totals = {}
        for user_data in account_data["users"].values():
            for part, p_data in user_data["partitions"].items():
                current_total = account_partition_totals.get(part, 0.0)
                account_partition_totals[part] = current_total + p_data["hours"]

        # Create subtable for account total (per partition)
        account_limit_dict = account_limits.get(account, {})
        account_total_subtable = Table()
        account_total_subtable.add_column("Partition", alignment="left")
        account_total_subtable.add_column("Hours", alignment="right")
        sorted_partitions = sorted(account_partition_totals.items(), key=lambda x: x[0])
        for part, total in sorted_partitions:
            limit = account_limit_dict.get(part, 0.0)
            total_str = f"{total:.2f}"
            if limit > 0:
                total_str += f" / {limit:.2f}"
            account_total_subtable.add_row([part, total_str])

        # Process users to gather valid entries
        valid_users = []
        for user, user_data in account_data["users"].items():
            user_total = sum(p["hours"] for p in user_data["partitions"].values())
            valid_users.append((user, user_data))

        if not valid_users:
            continue

        # Add account row to main table with placeholders
        table.add_row([account, "", ""])
        row_index = len(table.rows) - 1

        # Add account total subtable to column 1
        table.add_subtable(row_index, 1, account_total_subtable)

        # Build details table for user breakdown
        details_table = Table()
        details_table.add_column("User", alignment="left")
        details_table.add_column("User Total (Hours)", alignment="right")
        details_table.add_column("Partition Details", alignment="left")

        for user, user_data in sorted(valid_users, key=lambda x: x[0]):
            user_total = sum(p["hours"] for p in user_data["partitions"].values())
            # Do not sum quota across partitions: different partitions may
            # track different resource types (CPU-core-hours vs GPU-hours),
            # so a cross-partition total limit would be meaningless.
            user_total_str = f"{user_total:.2f}"

            partition_table = Table()
            partition_table.add_column("Partition", alignment="left")
            partition_table.add_column("Hours", alignment="right")
            sorted_user_partitions = sorted(
                user_data["partitions"].items(), key=lambda x: x[0]
            )
            for part, p_data in sorted_user_partitions:
                p_limit = user_data["limits"].get(part, {})
                limit = max(p_limit.get("gpu_limit", 0), p_limit.get("cpu_limit", 0))
                limit_str = f" / {limit:.2f}" if limit > 0 else ""
                partition_table.add_row([part, f"{p_data['hours']:.2f}{limit_str}"])

            details_table.add_row([user, user_total_str, ""])
            details_table.add_subtable(len(details_table.rows) - 1, 2, partition_table)

        # Add details subtable to column 2
        table.add_subtable(row_index, 2, details_table)

    return table.render()
