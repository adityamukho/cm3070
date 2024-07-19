import collections
import os
import pickle
import sys
import time

import numpy as np
import tmrl.config.config_constants as cfg


class State(object):
    def __init__(self):
        self.waypoints = None
        if not os.path.exists(cfg.REWARD_PATH):
            print("Reward path does not exist", file=sys.stderr)
            sys.exit(1)
        else:
            with open(cfg.REWARD_PATH, 'rb') as f:
                self.waypoints = pickle.load(f)

        assert self.waypoints is not None
        assert type(self.waypoints) is np.ndarray

        self.waypoints = iter(self.waypoints)
        self.target_waypoint = next(self.waypoints)

        self.timestamps = collections.deque(maxlen=2)
        self.positions = collections.deque(maxlen=2)
        self.velocities = collections.deque(maxlen=2)

        self.state_action_history = collections.deque(maxlen=200)

        self.finished = False

    def update(self, data, action):
        self.finished = data["is_finished"]
        if not self.finished:
            now = time.time()
            self.timestamps.append(now)

            position = np.array([data["x"], data["y"], data["z"]])
            self.positions.append(position)

            if len(self.positions) > 1:
                assert len(self.timestamps) > 1

                t_delta = self.timestamps[-1] - self.timestamps[-2]

                try:
                    velocity = (self.positions[-1] - self.positions[-2]) / t_delta
                    self.velocities.append(velocity)
                    print(np.linalg.norm(velocity), data["speed"])

                    if len(self.velocities) > 1:
                        acceleration = (self.velocities[-1] - self.velocities[-2]) / t_delta
                        anorm = np.linalg.norm(acceleration)

                        if np.isnan(anorm):
                            self.timestamps.pop()
                            self.positions.pop()
                            self.velocities.pop()
                        else:
                            acceleration /= anorm
                            self.state_action_history.append((acceleration, action))
                except ZeroDivisionError:
                    self.timestamps.pop()
                    self.positions.pop()
                    pass

    def lookup(self, target_acc):
        target_acc /= np.linalg.norm(target_acc)
        target_action = np.array([1.0, 0.0, 0.0])
        max_cos_sim = np.dot(np.array([1.0, 0.0, 0.0]), target_acc)

        it = iter(self.state_action_history)
        for t in it:
            acc = t[0]
            cos_sim = np.dot(acc, target_acc)
            if cos_sim > max_cos_sim:
                max_cos_sim = cos_sim
                target_action = t[1]

        return target_action
