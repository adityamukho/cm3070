import numpy as np
import pickle
from scipy.spatial.distance import euclidean
import os
import tmrl.config.config_constants as cfg

from .functions import reset_game, init_gamepad, get_data_dict, update_gamepad
from tmrl.custom.utils.tools import TM2020OpenPlanetClient

def load_waypoints():
    if not os.path.exists(cfg.REWARD_PATH):
        raise Exception("Reward path does not exist")
    else:
        with open(cfg.REWARD_PATH, 'rb') as f:
            waypoints = pickle.load(f)
    return waypoints

def find_nearest_waypoint(position, waypoints):
    distances = [euclidean(position, wp) for wp in waypoints]
    return np.argmin(distances)

def calculate_steering(current_position, target_position):
    direction = np.array(target_position) - np.array(current_position)
    angle = np.arctan2(direction[1], direction[0])
    return np.clip(angle / np.pi, -1, 1)

client = TM2020OpenPlanetClient()
gamepad = init_gamepad()
reset_game(gamepad)

waypoints = load_waypoints('reward.pkl')
current_waypoint_index = 0

while True:
    data = get_data_dict(client)

    if data["is_finished"]:
        break

    current_position = (data["x"], data["y"], data["z"])
    current_waypoint_index = find_nearest_waypoint(current_position, waypoints)
    target_waypoint = waypoints[min(current_waypoint_index + 1, len(waypoints) - 1)]

    steering = calculate_steering(current_position, target_waypoint)
    throttle = 1.0  # Always accelerate
    brake = 0.0  # Don't brake

    action = np.array([throttle, brake, steering])
    update_gamepad(gamepad, action)