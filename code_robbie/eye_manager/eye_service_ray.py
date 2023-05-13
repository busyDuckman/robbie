import math
import os
import sys
import time
import logging

import numpy as np
# import spidev as SPI
import spidev
sys.path.append("..")
from lib import LCD_1inch28
from PIL import Image, ImageDraw, ImageChops

from eye_render import render_eye
from scipy.ndimage import label
import ray

ray.init()

@ray.remote
class SharedState:
    def __init__(self):
        self.point_to_look_at = (0, 0, 1_000)
        self.shutdown_flag = False

    def update_point_to_look_at(self, new_point):
        self.point = new_point

    def get_point_to_look_at(self):
        return self.point

    def set_shutdown_flag(self):
        self.shutdown_flag = True

    def get_shutdown_flag(self):
        return self.shutdown_flag

@ray.remote
def update_state(shared_state):
    start_time = time.time()
    speed = 1
    while not ray.get(shared_state.get_shutdown_flag.remote()):
        elapsed_time = time.time() - start_time
        angle = 2 * math.pi * elapsed_time * speed
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        new_point = (x, y, 1_000)

        shared_state.update_point.remote(new_point)
        time.sleep(0.005)

@ray.remote
def render_loop(disp, pd, shared_state):
    # allocate display buffers
    img_buffers = [Image.new("RGB", (disp_left.width, disp_left.height), (0, 0, 0)) for _ in range(2)]
    draw_buffers = [ImageDraw.Draw(b) for b in img_buffers]

    # render loop
    frame = 0
    while not ray.get(shared_state.get_shutdown_flag.remote()):
        try:
            idx_draw = frame % 2
            idx_last = (frame + 1) % 2
            draw = draw_buffers[idx_draw]
            point_to_look_at = ray.get(shared_state.get_point_to_look_at.remote())

            render_eye(draw, (display.width, display.height), -buffer_offset * pd, point_to_look_at)

            bboxes = find_updated_regions(img_buffers[idx_last], img_buffers[idx_draw], 16)
            for box in bboxes:
                blit_window(display, img_buffers[idx_draw], box)

            frame += 1
        except IOError as e:
            logging.info(e)

def main_ray_not_working():
    # setup displays
    disp_left = LCD_1inch28.LCD_1inch28(bl=12)
    spi_1 = spidev.SpiDev(1, 0)
    display_right = LCD_1inch28.LCD_1inch28(spi=spi_1,
                                            rst=6, dc=26, bl=13)

    # Initialize displays
    disp_left.Init()
    disp_left.clear()
    display_right.Init()
    display_right.clear()

    # I have had mixed luck with python signals, lets see if this works.
    def signal_handler(sig, frame):
        shared_state.set_shutdown_flag.remote()

    signal.signal(signal.SIGINT, signal_handler)

    # shared mem
    shared_state = SharedState.remote()

    # start loops
    left_loop = render_loop.remote(disp_left, -3, shared_state)
    right_loop = render_loop.remote(disp_right, 3, shared_state)
    update_loop = update_state.remote(shared_state)
    ray.get([left_loop, right_loop, update_loop])

    # done (ctrl-c or shutdown message)
    print("Container shutdown.")
    disp_left.module_exit()
    display_right.module_exit()
    sys.exit(0)
