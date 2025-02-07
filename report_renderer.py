from table import Table


def render_report(usage_by_account, account_limits, title):
    table = Table(title=title)
    table.add_column("Account", alignment='left')
    table.add_column("Account Total (Hours)", alignment='right')
    table.add_column("Details", alignment='left')

    for account, account_data in usage_by_account.items():
        account_total = 0.0
        valid_users = []
        for user, user_data in account_data['users'].items():
            user_total = sum(p['hours']
                             for p in user_data['partitions'].values())
            valid_users.append((user, user_data))
            account_total += user_total

        if not valid_users:
            continue

        account_limit = sum(account_limits.get(account, {}).values())
        account_total_str = f"{account_total:.2f}"
        if account_limit > 0:
            account_total_str += f" / {account_limit:.2f}"

        details_table = Table()
        details_table.add_column("User", alignment='left')
        details_table.add_column("User Total (Hours)", alignment='right')
        details_table.add_column("Partition Details", alignment='left')

        for user, user_data in sorted(valid_users, key=lambda x: x[0]):
            user_total = sum(p['hours']
                             for p in user_data['partitions'].values())
            user_limit = sum(max(p_limit.get('gpu_limit', 0), p_limit.get('cpu_limit', 0))
                             for p_limit in user_data['limits'].values())
            user_total_str = f"{user_total:.2f}"
            if user_limit > 0:
                user_total_str += f" / {user_limit:.2f}"

            partition_table = Table()
            partition_table.add_column("Partition", alignment='left')
            partition_table.add_column("Hours", alignment='right')
            sorted_partitions = sorted(
                user_data['partitions'].items(), key=lambda x: x[0])
            for partition, p_data in sorted_partitions:
                p_limit = user_data['limits'].get(partition, {})
                limit = max(p_limit.get('gpu_limit', 0),
                            p_limit.get('cpu_limit', 0))
                limit_str = f" / {limit:.2f}" if limit > 0 else ""
                partition_table.add_row(
                    [partition, f"{p_data['hours']:.2f}{limit_str}"])

            details_table.add_row([user, user_total_str, ""])
            details_table.add_subtable(
                len(details_table.rows)-1, 2, partition_table)

        table.add_row([account, account_total_str, ""])
        table.add_subtable(len(table.rows)-1, 2, details_table)

    return table.render()
