# Slurm Helper Scripts: `squota` & `savail`

## Overview

This repository provides a suite of command-line tools designed to simplify resource management and monitoring on Slurm-based High-Performance Computing (HPC) clusters.

- `squota`: Python-based tool that generates detailed resource utilization reports (Account > User > Partition) and tracks usage against limits defined in Slurm associations.
- `savail`: Bash-based tool that provides a quick, color-coded summary of node availability within a specified partition, including CPU and GPU resources.

## Features

### `squota`
- Multi-level reporting: Account > User > Partition.
- Tracks usage against TRES limits from Slurm associations.
- Automatically filters "runaway" jobs (jobs present in `sacct` but not `squeue`) for more accurate reports.
- Customizable reporting period (start/end dates).
- Flexible filtering:
  - `-A/--account`: filter by account
  - `-u/--user`: filter by one or more users (repeatable or comma-separated)
  - `-p/--partition`: query one or more partitions
    - Default: only visible partitions (from `sinfo`)
    - If specified, the given partitions are used as-is (even if not visible)
- CSV export:
  - `--csv [lv1|lv2]` outputs CSV instead of the human-readable table
  - If `--csv` is provided without a value, defaults to `lv1`
  - Only one level at a time:
    - `lv1`: account-partition totals
    - `lv2`: account-user-partition details

### `savail`
- Color-coded output for node states (IDLE, MIXED, ALLOCATED, DRAIN, etc.).
- Displays available vs. total CPUs and GPUs for each node.
- Flexible sorting options: by available GPU (default), CPU, or node name.
- Option to show or hide unavailable (DRAIN/DOWN) nodes.

---

## Sample Output

### `squota` (Human-readable)
```text
$ squota -u bob -S 2024-09-01

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
└────────────┴───────────────────────┴───────────────────────────────────────────────────────────┘
Note: "Hours" refers to GPU-hour for GPU partitions and CPU-core-hour for CPU partitions.
```

### `squota` CSV

- Level 1 (account-partition totals)
```csv
$ squota --csv
Account,amd,intel,gpu-a30,gpu-l20,gpu-rtx5880
groupA,0.00,0.00,1192.72,0.00,0.00
groupB,431826.54,0.00,0.00,0.00,0.00
groupC,0.00,0.00,0.00,0.00,0.00
```

- Level 2 (account-user-partition details)
```csv
$ squota --csv lv2
Account,User,amd,intel,gpu-a30,gpu-l20,gpu-rtx5880
groupA,userA,0.00,0.00,1192.72,0.00,0.00
groupA,userB,1.00,0.00,1192.72,0.00,1.00
groupB,userC,431826.54,0.00,0.00,0.00,0.00
```

### `savail`
```bash
$ savail -p gpu-l20 --sort=gpu

Node   State  Available/TotalCPU  Available/TotalGPU
----------------------------------------------------
gpu17  IDLE          64/64                4/4       
gpu19  IDLE          64/64                4/4       
gpu20  IDLE          64/64                4/4       
gpu21  IDLE          64/64                4/4       
gpu16  MIXED         48/64                3/4
```

---

## Usage

- Filter by partitions (visible or not):
  - `squota -p gpu-a30,gpu-l20`
- Filter by multiple users:
  - `squota -u alice,bob`
- CSV export:
  - Default level (when no value given): `squota --csv` → `lv1`
  - Explicit level: `squota --csv lv1` or `squota --csv lv2`
- Human-readable table:
  - `squota -A mygroup -S 2024-09-01 -E 2024-09-30`

## Installation & Deployment

This project installs via a dedicated virtual environment (venv) under a configurable PREFIX and exposes thin wrappers in PREFIX/bin. No global pip, no system site‑packages, and no distro-specific packaging required.

### Prerequisites

- Python ≥ 3.9 available on the target host
- Python venv module installed
  - Debian/Ubuntu: `sudo apt install -y python3-venv`
  - RHEL/Rocky/CentOS: usually included with python3, else `sudo dnf install -y python3-venv`
- Optional: `uv` for building the wheel (or use any PEP 517 builder)

### Build (on any host)

1) Clone and prepare
```bash
git clone <your-repo-url>
cd slurm-helper-scripts
```

2) Build the wheel
```bash
uv build
# Produces: dist/slurm_helper_scripts-<VERSION>-py3-none-any.whl
```

Copy the built wheel to the target node(s) if building elsewhere.

### Install/Upgrade (on target nodes)

Use the provided Makefile to install into a system venv and link entrypoints:

- Default locations:
  - Venv: PREFIX/lib/slurm-helper-scripts/venv (default PREFIX=/usr/local)
  - Binaries: PREFIX/bin/{squota,savail}

Run one of the following:

- If running as root:
```bash
make install WHEEL=/path/to/slurm_helper_scripts-<VERSION>-py3-none-any.whl
```

- If using sudo:
```bash
make install SUDO=sudo WHEEL=/path/to/slurm_helper_scripts-<VERSION>-py3-none-any.whl
```

Notes:
- If WHEEL is omitted, Makefile will pick the newest wheel under ./dist.
- You can change the install prefix or Python used to create the venv:
  - `make install PREFIX=/usr`
  - `make install PYTHON_BIN=/usr/bin/python3.10`
- Re-running `make install` acts as an upgrade (it installs/updates the wheel inside the venv and relinks the wrappers).

After installation:
```bash
squota --help
savail --help
```

## License

MIT License. See the [LICENSE](LICENSE) file for details.