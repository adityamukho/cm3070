import numpy as np

from functions import reset_game, init_gamepad, get_data_dict, update_gamepad
from state import State
from tmrl.custom.utils.tools import TM2020OpenPlanetClient

client = TM2020OpenPlanetClient()
state = State()
gamepad = init_gamepad()
reset_game(gamepad)

action = np.array([1.0, 0.0, 0.0])
while True:
    data = get_data_dict(client)
    state.update(data, action)

    if state.finished:
        break

    action = state.lookup(action)
    update_gamepad(gamepad, action)
