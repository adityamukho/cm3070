import numpy as np
import pickle
from scipy.spatial.distance import euclidean
import os
import tmrl.config.config_constants as cfg
from collections import deque
import signal
import sys
import time

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
    target_yaw = np.arctan2(direction[1], direction[0])
    yaw_diff = target_yaw - orientation[1]  # Use yaw from orientation
    return np.clip(yaw_diff / np.pi, -1, 1)

def estimate_orientation(state_history):
    if len(state_history) < 2:
        return np.array([0, 0, 0])
    prev_pos = np.array(state_history[-2][:3])
    curr_pos = np.array(state_history[-1][:3])
    direction = curr_pos - prev_pos
    
    # Calculate pitch (rotation around x-axis)
    pitch = np.arctan2(direction[2], np.sqrt(direction[0]**2 + direction[1]**2))
    
    # Calculate yaw (rotation around z-axis)
    yaw = np.arctan2(direction[1], direction[0])
    
    # We can't directly calculate roll from position data
    # For simplicity, we'll assume roll is 0
    roll = 0
    
    return np.array([pitch, yaw, roll])

def is_car_stuck(state_history, threshold=0.1):
    if len(state_history) < 5:
        return False
    recent_positions = [np.array(state[:3]) for state in list(state_history)[-5:]]
    total_distance = sum(np.linalg.norm(recent_positions[i+1] - recent_positions[i]) for i in range(len(recent_positions)-1))
    return total_distance < threshold

def calculate_target_orientation(current_position, waypoints, current_waypoint_index, num_waypoints=3):
    target_waypoints = waypoints[current_waypoint_index:current_waypoint_index + num_waypoints]
    if len(target_waypoints) < num_waypoints:
        target_waypoints += waypoints[:num_waypoints - len(target_waypoints)]
    
    target_direction = np.mean([np.array(wp) - np.array(current_position) for wp in target_waypoints], axis=0)
    target_yaw = np.arctan2(target_direction[1], target_direction[0])
    return target_yaw

def adjust_throttle(state_history, action_history, current_position, waypoints, current_waypoint_index, standstill_threshold=0.01, standstill_duration=1.0):
    if len(state_history) < 2:
        return 1.0, False, 0.0
    
    curr_pos = np.array(state_history[-1][:3])
    prev_pos = np.array(state_history[-2][:3])
    distance = np.linalg.norm(curr_pos - prev_pos)
    
    current_time = state_history[-1][4]
    start_time = state_history[0][4]
    total_duration = current_time - start_time
    
    if distance < standstill_threshold and total_duration > standstill_duration:
        print(f"Stuck detected: distance={distance}, duration={total_duration}")
        target_yaw = calculate_target_orientation(current_position, waypoints, current_waypoint_index)
        return -0.5, True, target_yaw  # Reverse with half throttle and target yaw
    
    return 1.0, False, 0.0

def signal_handler(sig, frame):
    print("\nReceived Ctrl+C. Performing clean shutdown...")
    # Perform any necessary cleanup here
    if 'gamepad' in globals():
        update_gamepad(gamepad, np.array([0.0, 0.0, 0.0]))  # Stop the car
    if 'client' in globals():
        client.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

client = TM2020OpenPlanetClient()
gamepad = init_gamepad()
reset_game(gamepad)

waypoints = load_waypoints()
current_waypoint_index = 0

state_history = deque(maxlen=10)
action_history = deque(maxlen=10)
reversing_counter = 0

try:
    start_time = time.time()
    while True:
        data = get_data_dict(client)

        if data["is_finished"]:
            break

        current_time = time.time() - start_time
        current_position = (data["x"], data["y"], data["z"])
        state_history.append((data["x"], data["y"], data["z"], data["speed"], current_time))

        current_waypoint_index = find_nearest_waypoint(current_position, waypoints)
        target_waypoint = waypoints[min(current_waypoint_index + 1, len(waypoints) - 1)]

        orientation = estimate_orientation(state_history)
        throttle, should_reverse, target_yaw = adjust_throttle(state_history, action_history, current_position, waypoints, current_waypoint_index)
        
        if should_reverse:
            print("Reversing initiated")
            reversing_counter = 30  # Reverse for 30 frames
        
        if reversing_counter > 0:
            throttle = -0.5  # Maintain reverse throttle
            steering = calculate_steering(current_position, (current_position[0] + np.cos(target_yaw), current_position[1] + np.sin(target_yaw), current_position[2]), orientation)
            reversing_counter -= 1
            print(f"Reversing: counter={reversing_counter}, target_yaw={target_yaw}")
        else:
            steering = calculate_steering(current_position, target_waypoint, orientation)
        
        brake = 0.0 if throttle > 0 else 0.2  # Apply slight brake when reversing

        print(f"Throttle: {throttle}, Steering: {steering}, Brake: {brake}, Position: {current_position}")
        action = np.array([throttle, brake, steering])
        update_gamepad(gamepad, action)
        print(f"Action applied: {action}")
        action_history.append(action)

        # Limit the size of state_history to prevent memory issues
        if len(state_history) > 100:
            state_history.popleft()
        if len(action_history) > 100:
            action_history.popleft()

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    update_gamepad(gamepad, np.array([0.0, 0.0, 0.0]))  # Stop the car
    client.close()