import numpy as np
import pickle
from scipy.spatial.distance import euclidean
import os
import tmrl.config.config_constants as cfg
from collections import deque

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

def calculate_steering(current_position, target_position, orientation):
    direction = np.array(target_position) - np.array(current_position)
    target_angle = np.arctan2(direction[1], direction[0])
    angle_diff = target_angle - orientation
    return np.clip(angle_diff / np.pi, -1, 1)

def estimate_orientation(state_history):
    if len(state_history) < 2:
        return 0
    prev_pos = np.array(state_history[-2][:3])
    curr_pos = np.array(state_history[-1][:3])
    direction = curr_pos - prev_pos
    return np.arctan2(direction[1], direction[0])

def adjust_throttle(state_history, action_history):
    if len(state_history) < 2:
        return 1.0
    prev_pos = np.array(state_history[-2][:3])
    curr_pos = np.array(state_history[-1][:3])
    distance = np.linalg.norm(curr_pos - prev_pos)
    avg_throttle = np.mean([action[0] for action in action_history])
    if distance < 0.1 and avg_throttle > 0.8:
        return 0.5
    return 1.0

client = TM2020OpenPlanetClient()
gamepad = init_gamepad()
reset_game(gamepad)

waypoints = load_waypoints()
current_waypoint_index = 0

state_history = deque(maxlen=10)
action_history = deque(maxlen=10)

while True:
    data = get_data_dict(client)

    if data["is_finished"]:
        break

    current_position = (data["x"], data["y"], data["z"])
    state_history.append(current_position + (data["speed"],))

    current_waypoint_index = find_nearest_waypoint(current_position, waypoints)
    target_waypoint = waypoints[min(current_waypoint_index + 1, len(waypoints) - 1)]

    orientation = estimate_orientation(state_history)
    steering = calculate_steering(current_position, target_waypoint, orientation)
    throttle = adjust_throttle(state_history, action_history)
    brake = 0.0

    action = np.array([throttle, brake, steering])
    update_gamepad(gamepad, action)
    action_history.append(action)