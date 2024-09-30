# Slurm GPU Usage Reporter for MSc students

## Overview

This script generates a report of GPU usage on HKUST SuperPOD for MSc students. It provides a detailed breakdown of GPU hours used by account and partition, for tracking and managing resource utilization.

## Features

- Calculates GPU usage for a specified time period
- Breaks down usage by partition
- Compares usage against account GPU limits
- Supports filtering by date

## Usage
```bash
squota_msc [-h] [-u USERNAME] [-S START] [-E END] [-A ACCOUNT]
```

### Options

- `-h, --help`: Show the help message and exit
- `-u USERNAME, --username USERNAME`: Username to check usage for (optional)
- `-S START, --start START`: Start date for the report (YYYY-MM-DD)
- `-E END, --end END`: End date for the report (YYYY-MM-DD)
- `-A ACCOUNT, --account ACCOUNT`: Specific account to check (optional)

### Default Behavior

- If no dates are specified, the report will cover the current month (from the 1st to the current date)
- If no username is specified, it will use the current user
- Unless granted special permission, the user can only see the usage of itself

## Sample Output

```text
(base) username@slogin-01:~$ squota_msc

Using current user: username
Warning: Report includes today's date. Some very recent jobs may not be included due to accounting delays.
For most accurate results, wait a few minutes and run the report again.

GPU Usage report from 2024-09-01 to 2024-09-10
┌────────────────┬─────────────────────────────────┬──────────────────────┐
│    Account     │        Partition Details        │  Usage (GPU Hours)   │
├────────────────┼─────────────────────────────────┼──────────────────────┤
│ username       │ ┌───────────┬───────────────┐   │         0.05 / 30.00 │
│                │ │ Partition │   GPU Hours   │   │                      │
│                │ ├───────────┼───────────────┤   │                      │
│                │ │ normal    │          0.05 │   │                      │
│                │ └───────────┴───────────────┘   │                      │
└────────────────┴─────────────────────────────────┴──────────────────────┘
```

## Examples

1. Generate a report for the current user for the current month:
```bash
squota_msc
```
2. Generate a report for a specific date range:
```bash
squota_msc -S 2024-09-01 -E 2024-09-10
```
