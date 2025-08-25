# Slurm Helper Scripts: `squota` & `savail`

## Overview

This repository provides a suite of command-line tools designed to simplify resource management and monitoring on Slurm-based High-Performance Computing (HPC) clusters.

- **`squota`**: A powerful Python-based tool that generates detailed resource utilization reports. It offers a hierarchical view (Account > User > Partition) and tracks usage against limits defined in Slurm associations.
- **`savail`**: A handy Bash script that provides a quick, color-coded summary of node availability within a specified partition, including CPU and GPU resources.

## Features

### `squota`
- Multi-level reporting: Account > User > Partition.
- Tracks usage against TRES limits from Slurm associations.
- Automatically filters "runaway" jobs (jobs present in `sacct` but not `squeue`) for more accurate reports.
- Customizable reporting period (start/end dates).
- Ability to filter by a specific user or account.

### `savail`
- Color-coded output for node states (IDLE, MIXED, ALLOCATED, DRAIN, etc.).
- Displays available vs. total CPUs and GPUs for each node.
- Flexible sorting options: by available GPU (default), CPU, or node name.
- Option to show or hide unavailable (DRAIN/DOWN) nodes.

---

## Sample Output

### `squota`
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

## Installation & Deployment

This project ships platform packages built with fpm. Build once from source to produce .deb and .rpm, then install them with your system’s package manager.

### Prerequisites

- Python ≥ 3.9 is available on the build host.
- Ruby fpm installed on the build host:
  - Debian/Ubuntu: `sudo apt-get install ruby-dev gcc make && sudo gem install --no-document fpm`
  - RHEL/Rocky/CentOS: `sudo dnf install ruby-devel gcc make rpm-build && sudo gem install --no-document fpm`

### Build (on a build host)

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

3) Package into .deb and .rpm using the provided script
```bash
# Ensure the script is executable
chmod +x scripts/build_pkgs.sh
# Build packages (uses /usr/bin/python3 and installs under /usr/local)
./scripts/build_pkgs.sh
# Outputs: ./slurm-helper-scripts-<VERSION>-1.noarch.rpm and ./slurm-helper-scripts_<VERSION>_all.deb
```

Notes:
- The script forces /usr/bin/python3 and shebangs to avoid venv/conda bleed-through.
- Architecture is set via fpm’s `-a all` (per fpm docs), resulting in `all` for deb and `noarch` for rpm.

### Install (on target nodes)

- RPM-based (RHEL/Rocky/CentOS):
```bash
sudo dnf install ./slurm-helper-scripts-<VERSION>-1.noarch.rpm
```

- DEB-based (Debian/Ubuntu):
```bash
sudo apt install ./slurm-helper-scripts_<VERSION>_all.deb
```

After installation, the commands are available system-wide:
```bash
squota --help
savail --help
```

### Upgrade / Uninstall

- Upgrade:
  - Build a new wheel and re-run `./scripts/build_pkgs.sh`, then:
    - RPM: `sudo dnf upgrade ./slurm-helper-scripts-<NEWVER>-1.noarch.rpm`
    - DEB: `sudo apt install ./slurm-helper-scripts_<NEWVER>_all.deb`

- Uninstall:
  - RPM: `sudo dnf remove slurm-helper-scripts`
  - DEB: `sudo apt remove slurm-helper-scripts`

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.