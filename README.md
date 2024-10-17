# Slurm Usage Reporter

## Overview

This script generates a report of usage by partition on HKUST HPC4. It provides a detailed breakdown of unit hours (core-hour for cpu partitions, gpu-hour for gpu partitions) used by account and partition, for tracking and managing resource utilization.

## Features

- Calculates usage for a specified time period
- Breaks down usage by partition
- Supports filtering by date

## Usage
```bash
squota [-h] [-u USERNAME] [-S START] [-E END] [-A ACCOUNT]
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
bob@login1:~$ squota

Using current user: bob
Warning: Report includes today's date. Some very recent jobs may not be included due to accounting delays.
For most accurate results, wait a few minutes and run the report again.

     Usage report from 2024-10-01 to 2024-10-17
┌─────────┬─────────────┬──────────────────────────┐
│ Account │ Total (HKD) │    Partition Details     │
├─────────┼─────────────┼──────────────────────────┤
│ itsc    │       73.07 │ ┌───────────┬──────────┐ │
│         │             │ │ Partition │  Hours   │ │
│         │             │ ├───────────┼──────────┤ │
│         │             │ │ amd       │  4675.20 │ │
│         │             │ │ intel     │   528.33 │ │
│         │             │ │ gpu-l20   │     0.10 │ │
│         │             │ │ gpu-a30   │     0.01 │ │
│         │             │ └───────────┴──────────┘ │
└─────────┴─────────────┴──────────────────────────┘
```

## Examples

1. Generate a report for the current user for the current month:
```bash
squota
```
2. Generate a report for a specific date range:
```bash
squota -S 2024-09-01 -E 2024-09-10
```