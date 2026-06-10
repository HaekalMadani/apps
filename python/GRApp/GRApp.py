# GR App - Assetto Corsa in-game HUD app
#
# This file runs INSIDE the game, in AC's bundled Python 3.3 interpreter.
# Keep it 3.3-compatible: NO f-strings, NO type hints, NO pathlib tricks.
# The `ac` and `acsys` modules below are injected by the game at runtime.

import sys
import os

# AC puts this app folder on sys.path, but be explicit so sibling
# modules (GRApp_core) import reliably.
sys.path.insert(0, os.path.dirname(__file__))

import ac
import acsys

import GRApp_core as core

# Handles to the app window and labels (set in acMain).
app_window = 0
label_speed = 0
label_gear = 0
label_rpm = 0


def acMain(ac_version):
    """Called once when the app loads. Must return the app name."""
    global app_window, label_speed, label_gear, label_rpm

    app_window = ac.newApp("GR App")
    ac.setSize(app_window, 200, 120)
    ac.setTitle(app_window, "GR App")

    label_speed = ac.addLabel(app_window, "Speed: --")
    ac.setPosition(label_speed, 10, 30)

    label_gear = ac.addLabel(app_window, "Gear: --")
    ac.setPosition(label_gear, 10, 55)

    label_rpm = ac.addLabel(app_window, "RPM: --")
    ac.setPosition(label_rpm, 10, 80)

    return "GR App"


def acUpdate(deltaT):
    """Called every frame. deltaT is seconds since last call."""
    speed_kmh = ac.getCarState(0, acsys.CS.SpeedKMH)
    rpm = ac.getCarState(0, acsys.CS.RPM)
    gear = ac.getCarState(0, acsys.CS.Gear)

    ac.setText(label_speed, "Speed: " + core.format_speed(speed_kmh))
    ac.setText(label_gear, "Gear: " + core.format_gear(gear))
    ac.setText(label_rpm, "RPM: " + core.format_rpm(rpm))


def acShutdown():
    """Called when the app/session shuts down. Cleanup goes here."""
    pass
