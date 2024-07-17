import time

from tmrl.custom.utils.tools import TM2020OpenPlanetClient


client = TM2020OpenPlanetClient()

while True:
    data = client.retrieve_data(sleep_if_empty=0.01)
    print(data)
    time.sleep(1.0)
