from tmrl.custom.utils.tools import TM2020OpenPlanetClient

client = TM2020OpenPlanetClient()


def use_gamepad():
    import time
    from vgamepad import VX360Gamepad

    gamepad = VX360Gamepad()
    end_time = time.time() + 1
    data = []

    while time.time() < end_time:
        gamepad.right_trigger_float(value_float=1.0)  # gas
        gamepad.left_trigger_float(value_float=0.0)  # brake
        gamepad.left_joystick_float(0.0, 0.0)  # left/right
        gamepad.update()
        data = client.retrieve_data(sleep_if_empty=0.01)
        time.sleep(0.01)

    return data


data0 = client.retrieve_data(sleep_if_empty=0.01)
data1 = use_gamepad()

print(data0)
print(data1)

assert data1[0] > 0  # speed > 0
assert data1[1] > 0  # distance covered > 0

# At least one of x, y or z coordinates has changed
assert data0[2] != data1[2] or data0[3] != data1[3] or data0[4] != data1[4]

assert data1[5] == 0  # left/right not activated
assert data1[6] == 1.0  # forward full thrust
assert data1[7] == 0.0  # brakes not engaged
