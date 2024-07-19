import time

import tmrl.config.config_constants as cfg
from tmrl.custom.utils.control_gamepad import gamepad_reset, gamepad_close_finish_pop_up_tm20


def reset_game(gamepad=None):
    if gamepad is None:
        gamepad = init_gamepad()

    gamepad_close_finish_pop_up_tm20(gamepad)
    gamepad_reset(gamepad)
    time.sleep(cfg.SLEEP_TIME_AT_RESET)


def init_gamepad():
    from vgamepad import VX360Gamepad

    return VX360Gamepad()


def update_gamepad(gamepad, action):
    gamepad.right_trigger_float(value_float=action[0])  # gas
    gamepad.left_trigger_float(value_float=action[1])
    gamepad.left_joystick_float(action[2], 0.0)  # left/right

    gamepad.update()


def get_data_dict(client):
    data = client.retrieve_data(sleep_if_empty=0.01)
    data_dict = {
        "speed": data[0],
        "distance": data[1],
        "x": data[2],
        "y": data[3],
        "z": data[4],
        "turn": data[5],
        "gas": data[6],
        "is_braking": bool(data[7]),
        "is_finished": bool(data[8]),
        "gear": int(data[9]),
        "rmp": data[10],
    }

    return data_dict


def update_action(gamepad, fwd=0.0, back=0.0, turn=0.0):
    assert 0 <= fwd <= 1
    assert 0 <= back <= 1
    assert -1 <= turn <= 1

    gamepad.right_trigger_float(value_float=fwd)
    gamepad.left_trigger_float(value_float=back)
    gamepad.left_joystick_float(turn, 0.0)
    gamepad.update()
