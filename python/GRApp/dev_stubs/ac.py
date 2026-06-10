# Stub of Assetto Corsa's built-in `ac` module.
#
# FOR LOCAL EDITING / LINTING / AUTOCOMPLETE ONLY. Inside the game, AC injects
# the real `ac` module and this file is never used. Do NOT add this folder to
# sys.path when running in-game, or it will shadow the real module.
#
# Extend with more functions as you use them. Full reference: AC Python docs.


def newApp(name):
    return 0


def setSize(app, w, h):
    pass


def setTitle(app, title):
    pass


def setPosition(control, x, y):
    pass


def addLabel(app, text):
    return 0


def setText(control, text):
    return 0


def setFontSize(control, size):
    pass


def setFontColor(control, r, g, b, a):
    pass


def getCarState(car_id, state, *args):
    return 0


def log(message):
    pass


def console(message):
    pass
