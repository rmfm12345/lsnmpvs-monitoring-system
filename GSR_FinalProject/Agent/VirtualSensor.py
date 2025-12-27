import random
import time
import math

class VirtualSensor:
    def __init__(self, min_val=0, max_val=100, sampling_rate=1, sensor_type="Standard"):
        self.min = min_val
        self.max = max_val
        self.sampling_rate = sampling_rate
        self.last_sample = 0
        self.last_sample_time = 0
        self.current_value = random.randint(min_val, max_val)
        self.type = sensor_type

    def read(self):
        self.last_sample_time = time.time()
        return random.randint(self.min, self.max)

    def should_sample(self, current_time):
        """Calculo para o beacon loop no agent"""
        return current_time - self.last_sample >= (1.0 / self.sampling_rate)

    def update_last_sample(self, current_time):
        self.last_sample = current_time

    def set_sampling_rate(self, new_rate):
        self.sampling_rate = new_rate
