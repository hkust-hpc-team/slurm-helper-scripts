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

This project uses `uv` and `setuptools`. The deployment process involves two main stages: **Development/Build** on a head node and **Installation** on login nodes.

### Prerequisites

- A Python version >= 3.9.
- `uv` installed. If not present, you can install it via:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### Stage 1: Development and Building (On a Head Node or Build Environment)

These steps are for developers or administrators who need to modify the code or build the installation package.

1.  **Clone the Repository**
    ```bash
    git clone <your-repo-url>
    cd slurm-helper-scripts
    ```

2.  **Set up the Development Environment**
    ```bash
    uv sync
    ```

3.  **Run Tools for Testing**
    You can now run `squota` and `savail` directly within the development environment using `uv run`.

    *   **Running `squota`**:
        ```bash
        uv run squota --help
        uv run squota -u <username>
        ```

    *   **Running `savail`**:
        ```bash
        uv run savail -p cpu
        ```

4.  **Build the Distribution Package**
    Once development and testing are complete, build the distributable wheel (`.whl`) file. This command packages everything into a single file for easy installation.
    ```bash
    uv build
    ```
    This will create a `.whl` file in the `dist/` directory, for example: `dist/slurm_helper_scripts-1.1.0-py3-none-any.whl`. This is the file you will deploy.

### Stage 2: System-Wide Installation (On Login Nodes)

These steps are for deploying the tools to make them available to all users on the login nodes. **This typically requires `sudo` privileges.**

1.  **Copy the Wheel File to a Shared Location**
    Place the `.whl` file from the `dist/` directory onto a shared filesystem that all login nodes can access.
    ```bash
    # Example:
    cp dist/slurm_helper_scripts-1.1.0-py3-none-any.whl /path/to/shared/packages/
    ```

2.  **Install on Each Login Node**
    Log in to **each login node** and run the following command to perform a system-wide installation.

    *   **Using `uv` (Recommended)**:
        ```bash
        sudo uv pip install /path/to/shared/packages/slurm_helper_scripts-1.1.0-py3-none-any.whl
        ```

    *   **Using `pip` (If `uv` is not installed on login nodes)**:
        ```bash
        sudo pip3 install /path/to/shared/packages/slurm_helper_scripts-1.1.0-py3-none-any.whl
        ```
    After installation, the `squota` and `savail` commands will be available in the system's standard path (e.g., `/usr/local/bin`) for all users.

3.  **Verify the Installation**
    On any login node, users should now be able to run the commands directly:
    ```bash
    squota -h
    savail -h
    ```

### Upgrading or Uninstalling

-   **To upgrade**, build the new version (e.g., `1.2.0`), copy the new `.whl` file, and re-run the `sudo uv pip install --upgrade ...` command on each login node.
-   **To uninstall**, run the following command on each login node:
    ```bash
    sudo uv pip uninstall slurm-helper-scripts
    ```

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.