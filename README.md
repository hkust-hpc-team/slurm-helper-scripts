# Slurm Usage Reporter

## Overview

This script generates detailed resource utilization reports for HPC clusters using Slurm. 

## Features

- Multi-level reporting (Account > User > Partition)
- Usage cap tracking from Slurm associations

## Usage
```bash
squota [-h] [-u USERNAME] [-S START] [-E END] [-A ACCOUNT]
```

### Key Options

- `-A,--account`: Show specific account usage
- `-S,--start`: Start date (YYYY-MM-DD)
- `-E,--end`: End date (YYYY-MM-DD)
- `-u,--username`: Check specific user

## Sample Output after installation
```text
(base) bob@slogin-01:~$squota -u bob -S 2024-09-01

Usage report from 2024-09-01 to 2025-02-06                            
┌────────────┬───────────────────────┬───────────────────────────────────────────────────────────┐
│  Account   │ Account Total (Hours) │                          Details                          │
├────────────┼───────────────────────┼───────────────────────────────────────────────────────────┤
│ itscspod   │                 18.75 │ ┌──────────┬────────────────────┬───────────────────────┐ │
│            │                       │ │   User   │ User Total (Hours) │   Partition Details   │ │
│            │                       │ ├──────────┼────────────────────┼───────────────────────┤ │
│            │                       │ │ bob      │              18.75 │ ┌───────────┬───────┐ │ │
│            │                       │ │          │                    │ │ Partition │ Hours │ │ │
│            │                       │ │          │                    │ ├───────────┼───────┤ │ │
│            │                       │ │          │                    │ │ admin     │ 11.57 │ │ │
│            │                       │ │          │                    │ │ cpu       │  0.02 │ │ │
│            │                       │ │          │                    │ │ large     │  4.39 │ │ │
│            │                       │ │          │                    │ │ normal    │  2.76 │ │ │
│            │                       │ │          │                    │ └───────────┴───────┘ │ │
│            │                       │ └──────────┴────────────────────┴───────────────────────┘ │
│ myaccount  │                  0.22 │ ┌──────────┬────────────────────┬───────────────────────┐ │
│            │                       │ │   User   │ User Total (Hours) │   Partition Details   │ │
│            │                       │ ├──────────┼────────────────────┼───────────────────────┤ │
│            │                       │ │ bob      │               0.22 │ ┌───────────┬───────┐ │ │
│            │                       │ │          │                    │ │ Partition │ Hours │ │ │
│            │                       │ │          │                    │ ├───────────┼───────┤ │ │
│            │                       │ │          │                    │ │ normal    │  0.22 │ │ │
│            │                       │ │          │                    │ └───────────┴───────┘ │ │
│            │                       │ └──────────┴────────────────────┴───────────────────────┘ │
│ mscbdt2024 │                  0.15 │ ┌──────────┬────────────────────┬───────────────────────┐ │
│            │                       │ │   User   │ User Total (Hours) │   Partition Details   │ │
│            │                       │ ├──────────┼────────────────────┼───────────────────────┤ │
│            │                       │ │ bob      │               0.15 │ ┌───────────┬───────┐ │ │
│            │                       │ │          │                    │ │ Partition │ Hours │ │ │
│            │                       │ │          │                    │ ├───────────┼───────┤ │ │
│            │                       │ │          │                    │ │ normal    │  0.15 │ │ │
│            │                       │ │          │                    │ └───────────┴───────┘ │ │
│            │                       │ └──────────┴────────────────────┴───────────────────────┘ │
└────────────┴───────────────────────┴───────────────────────────────────────────────────────────┘
Note: "Hours" refers to GPU-hour for GPU partitions and CPU-core-hour for CPU partitions.
To convert GPU-hour to GPU-node-hour, divide GPU-hour by 8.
```

## Installation
```bash
sudo ./install.sh
```

## License
MIT Licensed - See LICENSE file