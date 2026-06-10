import os
import sys

# Make GRApp_core importable without installing anything.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import GRApp_core as core


def test_format_gear_reverse():
    assert core.format_gear(0) == "R"


def test_format_gear_neutral():
    assert core.format_gear(1) == "N"


def test_format_gear_first():
    assert core.format_gear(2) == "1"


def test_format_gear_sixth():
    assert core.format_gear(7) == "6"


def test_format_speed_rounds():
    assert core.format_speed(99.6) == "100 km/h"


def test_format_rpm_rounds():
    assert core.format_rpm(7345.2) == "7345"
