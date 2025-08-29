#!/usr/bin/env python3
"""
SLURM Node Resource Availability Viewer

A tool to display resource summary for all nodes within a specified partition.
Features:
  - Dynamic column widths for clean layout
  - ANSI color-coding for node state and resource availability
  - Flexible sorting options (GPU, CPU, or node name)
  - Natural sorting for node names (handles numbers correctly)
  - State-based prioritization (IDLE > MIXED > ALLOCATED)
  - Option to show/hide unavailable nodes
"""

import argparse
import subprocess
import sys
import re
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum


class SortBy(Enum):
    """Sorting options for node display"""
    GPU = "gpu"
    CPU = "cpu"
    NODE = "node"


class Colors:
    """ANSI color codes for terminal output"""
    RED = "\033[31m"
    YELLOW = "\033[33m"
    GREEN = "\033[32m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    RESET = "\033[0m"


@dataclass
class NodeInfo:
    """Data class for node information"""
    name: str
    state: str
    cpu_total: int
    cpu_alloc: int
    gpu_total: int
    gpu_alloc: int
    
    @property
    def cpu_avail(self) -> int:
        return self.cpu_total - self.cpu_alloc
    
    @property
    def gpu_avail(self) -> int:
        return self.gpu_total - self.gpu_alloc
    
    @property
    def cpu_percent(self) -> float:
        return self.cpu_avail / self.cpu_total if self.cpu_total > 0 else 0
    
    @property
    def gpu_percent(self) -> float:
        return self.gpu_avail / self.gpu_total if self.gpu_total > 0 else 0
    
    @property
    def is_unavailable(self) -> bool:
        return any(s in self.state for s in ["DRAIN", "DOWN", "INVALID"])
    
    @property
    def state_priority(self) -> int:
        """
        Return state priority for sorting (lower value = higher priority).
        
        Priority order:
        1. IDLE (most available)
        2. MIXED (partially available)
        3. ALLOCATED (not available)
        4. DRAIN/DOWN/INVALID (unavailable)
        
        Returns:
            Integer representing state priority
        """
        # Remove any modifiers (e.g., IDLE+DRAIN becomes IDLE for base state)
        base_state = self.state.split('+')[0]
        
        if self.is_unavailable:
            return 4
        elif base_state == "IDLE":
            return 1
        elif base_state == "MIXED":
            return 2
        elif base_state == "ALLOCATED":
            return 3
        else:
            return 5  # Unknown states go last


def natural_sort_key(text: str) -> List[Union[int, str]]:
    """
    Generate a key for natural sorting of strings containing numbers.
    
    This function splits a string into alternating text and number parts,
    converting numbers to integers for proper numerical comparison.
    
    Example:
        "gpu11" -> ["gpu", 11]
        "gpu101" -> ["gpu", 101]
        So gpu11 sorts before gpu101
    
    Args:
        text: String to generate sort key for
        
    Returns:
        List of alternating strings and integers for sorting
    """
    parts = []
    for match in re.finditer(r'(\d+|\D+)', text):
        part = match.group(0)
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(part.lower())
    return parts


def run_command(cmd: List[str]) -> str:
    """
    Execute a shell command and return output.
    
    Args:
        cmd: Command and arguments as list
        
    Returns:
        Command output as string
        
    Raises:
        SystemExit: If command fails
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(cmd)}", file=sys.stderr)
        print(f"Error message: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}", file=sys.stderr)
        print("Make sure SLURM commands are available in your PATH", file=sys.stderr)
        sys.exit(1)


def get_node_list(partition: str) -> List[str]:
    """
    Get expanded list of nodes in partition.
    
    Args:
        partition: SLURM partition name
        
    Returns:
        List of node names
        
    Raises:
        SystemExit: If partition not found or empty
    """
    # Get compressed node list
    compressed = run_command(["sinfo", "-h", "-p", partition, "-o", "%N"])
    if not compressed:
        print(f"Error: Partition '{partition}' not found or contains no nodes.", file=sys.stderr)
        sys.exit(1)
    
    # Expand node list
    expanded = run_command(["scontrol", "show", "hostnames", compressed])
    return expanded.split('\n') if expanded else []


def parse_node_info(node_output: str) -> Optional[NodeInfo]:
    """
    Parse node information from scontrol output.
    
    Args:
        node_output: Raw output from scontrol show node
        
    Returns:
        NodeInfo object or None if parsing fails
    """
    # Extract node name
    name_match = re.search(r'NodeName=(\S+)', node_output)
    if not name_match:
        return None
    
    name = name_match.group(1)
    
    # Extract state
    state_match = re.search(r'State=(\S+)', node_output)
    state = state_match.group(1) if state_match else "UNKNOWN"
    
    # Extract CPU info
    cpu_tot_match = re.search(r'CPUTot=(\d+)', node_output)
    cpu_alloc_match = re.search(r'CPUAlloc=(\d+)', node_output)
    cpu_total = int(cpu_tot_match.group(1)) if cpu_tot_match else 0
    cpu_alloc = int(cpu_alloc_match.group(1)) if cpu_alloc_match else 0
    
    # Extract GPU info from CfgTRES and AllocTRES
    gpu_total = 0
    gpu_alloc = 0
    
    cfg_match = re.search(r'CfgTRES=.*gres/gpu=(\d+)', node_output)
    if cfg_match:
        gpu_total = int(cfg_match.group(1))
    
    alloc_match = re.search(r'AllocTRES=.*gres/gpu=(\d+)', node_output)
    if alloc_match:
        gpu_alloc = int(alloc_match.group(1))
    
    return NodeInfo(name, state, cpu_total, cpu_alloc, gpu_total, gpu_alloc)


def get_nodes_info(node_list: List[str]) -> List[NodeInfo]:
    """
    Get detailed information for all nodes.
    
    Args:
        node_list: List of node names
        
    Returns:
        List of NodeInfo objects
    """
    # Get all node information at once
    output = run_command(["scontrol", "show", "node"])
    
    # Split by node entries
    node_entries = output.split('\n\n')
    
    # Create set of target nodes for faster lookup
    target_nodes = set(node_list)
    
    nodes_info = []
    for entry in node_entries:
        if not entry.strip():
            continue
        
        node_info = parse_node_info(entry)
        if node_info and node_info.name in target_nodes:
            nodes_info.append(node_info)
    
    return nodes_info


def colorize_state(state: str) -> str:
    """
    Apply color to node state.
    
    Args:
        state: Node state string
        
    Returns:
        Colorized state string
    """
    parts = state.split('+')
    colored_parts = []
    
    for part in parts:
        if part == "IDLE":
            color = Colors.GREEN
        elif part == "MIXED":
            color = Colors.YELLOW
        elif part == "ALLOCATED":
            color = Colors.RED
        elif part == "DRAIN":
            color = Colors.MAGENTA
        elif part == "DOWN":
            color = Colors.RED
        elif "INVALID" in part:
            color = Colors.CYAN
        else:
            color = Colors.RESET
        
        colored_parts.append(f"{color}{part}{Colors.RESET}")
    
    return '+'.join(colored_parts)


def colorize_resource(avail: int, total: int) -> str:
    """
    Apply color to resource availability string.
    
    Args:
        avail: Available resources
        total: Total resources
        
    Returns:
        Colorized resource string
    """
    if total == 0:
        color = Colors.RESET
    elif avail == 0:
        color = Colors.RED
    elif avail == total:
        color = Colors.GREEN
    else:
        color = Colors.YELLOW
    
    return f"{color}{avail:>9}/{total:<8}{Colors.RESET}"


def sort_nodes(nodes: List[NodeInfo], sort_by: SortBy, show_unavail: bool) -> List[NodeInfo]:
    """
    Sort nodes according to specified criteria with natural sorting for node names.
    
    For GPU and CPU sorting:
    1. Unavailable nodes (DRAIN/DOWN/INVALID) are placed last
    2. Primary sort by resource availability percentage (descending)
    3. Secondary sort by state priority (IDLE > MIXED > ALLOCATED)
    4. Tertiary sort by node name (natural sorting)
    
    For NODE sorting:
    - Natural alphabetical sorting by node name
    
    Args:
        nodes: List of NodeInfo objects
        sort_by: Sorting criterion
        show_unavail: Whether to show unavailable nodes
        
    Returns:
        Sorted list of NodeInfo objects
    """
    # Filter out unavailable nodes if requested
    if not show_unavail:
        nodes = [n for n in nodes if not n.is_unavailable]
    
    # Sort based on criteria
    if sort_by == SortBy.NODE:
        # Natural sort by node name
        return sorted(nodes, key=lambda n: natural_sort_key(n.name))
    elif sort_by == SortBy.CPU:
        # Sort by CPU availability with state priority and natural node name
        return sorted(nodes, key=lambda n: (
            n.is_unavailable,                    # Unavailable nodes last
            -n.cpu_percent,                      # Higher availability first
            n.state_priority,                    # IDLE before MIXED before ALLOCATED
            natural_sort_key(n.name)             # Natural sort for node names
        ))
    else:  # GPU (default)
        # Sort by GPU availability with state priority and natural node name
        return sorted(nodes, key=lambda n: (
            n.is_unavailable,                    # Unavailable nodes last
            -n.gpu_percent,                      # Higher availability first
            n.state_priority,                    # IDLE before MIXED before ALLOCATED
            natural_sort_key(n.name)             # Natural sort for node names
        ))


def print_table(nodes: List[NodeInfo]) -> None:
    """
    Print formatted table of node information.
    
    Args:
        nodes: List of NodeInfo objects to display
    """
    if not nodes:
        print("No nodes to display")
        return
    
    # Calculate column widths
    max_name_len = max(len(n.name) for n in nodes)
    max_state_len = max(len(n.state) for n in nodes)
    
    # Ensure minimum widths for headers
    max_name_len = max(max_name_len, 4)   # "Node"
    max_state_len = max(max_state_len, 5)  # "State"
    
    # Print header
    header = f"{'Node':<{max_name_len}}  {'State':<{max_state_len}}  {'Available/TotalCPU':<19}  {'Available/TotalGPU':<19}"
    print(header)
    print('-' * len(header))
    
    # Print nodes
    for node in nodes:
        colored_state = colorize_state(node.state)
        colored_cpu = colorize_resource(node.cpu_avail, node.cpu_total)
        colored_gpu = colorize_resource(node.gpu_avail, node.gpu_total)
        
        # Account for ANSI codes in state string for proper alignment
        state_padding = max_state_len + (len(colored_state) - len(node.state))
        
        print(f"{node.name:<{max_name_len}}  {colored_state:<{state_padding}}  {colored_cpu}  {colored_gpu}")


def run():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Display resource summary for SLURM partition nodes",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "-p", "--partition",
        required=True,
        help="SLURM partition name"
    )
    
    parser.add_argument(
        "--sort",
        type=str,
        choices=["gpu", "cpu", "node"],
        default="gpu",
        help="Sort by: gpu (default), cpu, or node name"
    )
    
    parser.add_argument(
        "--show-unavail",
        action="store_true",
        help="Show unavailable nodes (DRAIN/DOWN/INVALID)"
    )
    
    args = parser.parse_args()
    
    try:
        # Get node list
        node_list = get_node_list(args.partition)
        
        # Get detailed node information
        nodes_info = get_nodes_info(node_list)
        
        # Sort nodes
        sort_by = SortBy(args.sort)
        sorted_nodes = sort_nodes(nodes_info, sort_by, args.show_unavail)
        
        # Display table
        print_table(sorted_nodes)
        
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)