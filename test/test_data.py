from tmrl.custom.utils.tools import TM2020OpenPlanetClient

from kane.functions import reset_game

reset_game()
client = TM2020OpenPlanetClient()
data = client.retrieve_data(sleep_if_empty=0.01)
print(data)

assert isinstance(data, tuple)
assert len(data) == 11
assert all(isinstance(d, float) for d in data)
assert data[0] < 0.01  # speed is ~0
assert data[1] == 0.0  # total distance travelled is 0
# data[2:5] == x, y, z coordinates
assert data[5] == 0.0  # left/right not activated
assert data[6] == 0.0  # fowrward / backward not activated
assert data[7] == 0.0  # brakes not engaged
assert data[8] == 0.0  # game not finished
assert data[9] == 1.0  # gear is 1
assert data[10] < 150  # rpm is at idle speed
