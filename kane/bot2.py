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

def calculate_steering(current_position, waypoints, current_waypoint_index, num_waypoints=50, smoothing_factor=0.7):
    target_waypoints = waypoints[current_waypoint_index:current_waypoint_index + num_waypoints]
    if len(target_waypoints) < num_waypoints:
        target_waypoints += waypoints[:num_waypoints - len(target_waypoints)]
    
    target_direction = np.mean([np.array(wp[:2]) - np.array(current_position[:2]) for wp in target_waypoints], axis=0)
    target_yaw = np.arctan2(target_direction[1], target_direction[0])
    
    current_yaw = estimate_orientation(state_history)
    yaw_diff = target_yaw - current_yaw
    
    # Normalize yaw_diff to be between -pi and pi
    yaw_diff = (yaw_diff + np.pi) % (2 * np.pi) - np.pi
    
    # Invert the steering direction and apply smoothing factor
    return np.clip(-yaw_diff * smoothing_factor, -1, 1)

def estimate_orientation(state_history):
    if len(state_history) < 2:
        return 0.0
    prev_pos = np.array(state_history[-2][:2])  # Only consider x and y
    curr_pos = np.array(state_history[-1][:2])  # Only consider x and y
    direction = curr_pos - prev_pos
    
    # Calculate yaw (rotation around z-axis)
    yaw = np.arctan2(direction[1], direction[0])
    
    return yaw

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

def adjust_throttle(state_history, action_history, current_position, waypoints, current_waypoint_index, orientation, standstill_threshold=0.01, standstill_duration=1.0):
    if len(state_history) < 2:
        return 1.0, False, 0.0, 0

    curr_pos = np.array(state_history[-1][:2])  # Only consider x and y
    prev_pos = np.array(state_history[-2][:2])  # Only consider x and y
    distance = np.linalg.norm(curr_pos - prev_pos)
    
    current_time = state_history[-1][4]
    start_time = state_history[0][4]
    total_duration = current_time - start_time
    
    if distance < standstill_threshold and total_duration > standstill_duration:
        print(f"Stuck detected: distance={distance}, duration={total_duration}")
        target_yaw = calculate_target_orientation(current_position, waypoints, current_waypoint_index)
        yaw_diff = target_yaw - orientation
        
        # Normalize yaw_diff to be between -pi and pi
        yaw_diff = (yaw_diff + np.pi) % (2 * np.pi) - np.pi
        
        # Calculate steering based on yaw difference
        steering = np.clip(yaw_diff / np.pi, -1, 1)
        
        return -0.5, True, steering, 5  # Reverse with steering for 5 seconds
    
    return 1.0, False, 0.0, 0

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
    previous_steering = 0
    reversing_time = 0
    while True:
        data = get_data_dict(client)

        if data["is_finished"]:
            break

        current_time = time.time() - start_time
        current_position = (data["x"], data["y"], data["z"])
        state_history.append((data["x"], data["y"], data["z"], data["speed"], current_time))

        current_waypoint_index = find_nearest_waypoint(current_position, waypoints)

        orientation = estimate_orientation(state_history)
        throttle, should_reverse, steering, reverse_duration = adjust_throttle(state_history, action_history, current_position, waypoints, current_waypoint_index, orientation)
        
        if should_reverse:
            if reversing_time == 0:
                reversing_time = time.time()
            elif time.time() - reversing_time >= reverse_duration:
                should_reverse = False
                reversing_time = 0
        else:
            reversing_time = 0
            steering = calculate_steering(current_position, waypoints, current_waypoint_index)

        # Apply less smoothing to steering for harder turns
        steering = 0.8 * steering + 0.2 * previous_steering
        previous_steering = steering

        brake = 0.0 if throttle > 0 else 0.2  # Apply slight brake when reversing

        print(f"Throttle: {throttle}, Steering: {steering}, Brake: {brake}, Position: {current_position}, Reversing: {should_reverse}")
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