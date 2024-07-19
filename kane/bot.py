import numpy as np

from functions import reset_game, init_gamepad, get_data_dict, update_gamepad
from state import State

state = State()
gamepad = init_gamepad()
reset_game(gamepad)

action = np.array([1.0, 0.0, 0.0])
while True:
    data = get_data_dict()
    state.update(data, action)

    if state.finished:
        break

    action = state.lookup(action)
    update_gamepad(gamepad, action)


