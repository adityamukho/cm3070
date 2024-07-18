import time

from tmrl.custom.utils.tools import TM2020OpenPlanetClient
from vgamepad import VX360Gamepad

client = TM2020OpenPlanetClient()
gamepad = VX360Gamepad()
data = []

while not len(data) or data[8] == 0.0:
    data = client.retrieve_data(sleep_if_empty=0.01)
    gamepad.right_trigger_float(value_float=1.0)
    time.sleep(0.01)

print('Finished.')

