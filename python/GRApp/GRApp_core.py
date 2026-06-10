# Pure logic for GR App.
#
# Deliberately has NO `ac` / `acsys` imports, so every function here can be
# unit-tested in the conda dev env (see tests/). Keep it 3.3-compatible.


def format_gear(gear):
    """AC reports gear as 0=reverse, 1=neutral, 2=1st gear, 3=2nd, ..."""
    if gear == 0:
        return "R"
    if gear == 1:
        return "N"
    return str(gear - 1)


def format_speed(speed_kmh):
    return "{0} km/h".format(int(round(speed_kmh)))


def format_rpm(rpm):
    return str(int(round(rpm)))
