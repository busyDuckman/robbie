import numpy as np


class EyeLid:
    def __init__(self, num_curve_points, closed_curve_pos):
        self.num_curve_points = num_curve_points
        self.resting_curve_target = np.zeros((num_curve_points, 2))
        self.resting_curve_current = np.zeros((num_curve_points, 2))
        self.closed_curve_pos = closed_curve_pos
        self.current_curve = np.zeros((num_curve_points, 2))

    def set_curve(self, curve):
        self.resting_curve_target = curve

    def update(self, dt, blink_cycle_progress, blink_speed, rest_change_speed):
        # Update resting_curve_current towards resting_curve_target
        self.resting_curve_current += (self.resting_curve_target - self.resting_curve_current) * rest_change_speed * dt

        # Compute the openness
        openness = abs(blink_cycle_progress * 2 - 1)
        # openness = self.speed_transform(openness - 0.5)

        # Update the current curve
        self.current_curve = self.resting_curve_current * openness + self.closed_curve_pos * (1 - openness)

    @staticmethod
    def speed_transform(x):
        return 0.5 * (1 + np.cos(np.pi * (x - 0.5)))

class EyeLidManager:
    def __init__(self, num_curve_points, closed_curve_pos, ibi, blink_speed, rest_change_speed):
        self.upper_lid = EyeLid(num_curve_points, closed_curve_pos)
        self.lower_lid = EyeLid(num_curve_points, closed_curve_pos)
        self.ibi = ibi
        self.blink_speed = blink_speed
        self.rest_change_speed = rest_change_speed
        self.last_blink_time = 0
        self.blink_cycle_progress = 0

    def update(self, dt):
        self.blink_cycle_progress += dt * self.blink_speed
        self.blink_cycle_progress %= 1

        self.upper_lid.update(dt, self.blink_cycle_progress, self.blink_speed, self.rest_change_speed)
        self.lower_lid.update(dt, self.blink_cycle_progress, self.blink_speed, self.rest_change_speed)

