import socket


def parse_tres(tres_str):
    """Given a TRES string, return a dictionary of resource limits."""
    if not tres_str:
        return {}
    tres_dict = {}
    for item in tres_str.split(','):
        if '=' in item:
            key, value = item.split('=')
            tres_dict[key] = int(value)
    return tres_dict


def parse_time(time_str_in_second):
    """Convert elapsed time (in seconds) to hours."""
    seconds = int(time_str_in_second)
    return seconds / 3600  # Convert seconds to hours


def get_cluster() -> str:
    """Return the cluster name, determined by the hostname.
    The function returns one of the following values:
    - hpc4: HPC4 cluster
    - superpod: SuperPOD cluster
    - unknown: Unknown cluster
    """
    hostname = socket.gethostname()
    hpc4_hosts = ["login1", "login2", "hpc4head-01", "hpc4head-02"]
    superpod_hosts = ["slogin-01", "slogin-02",
                      "bcm2suheadnode-01", "bcm2suheadnode-02"]
    if hostname in hpc4_hosts:
        return "hpc4"
    elif hostname in superpod_hosts:
        return "superpod"
    else:
        return "unknown"
