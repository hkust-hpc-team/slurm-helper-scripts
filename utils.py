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
