"""
Two 3.3v displays (left and right), powered via:
  - VCC:   ->  3.3V pin (1 or 17)
  - GND:   ->  GND pin  (9, 6, 14, 20, 30, 34)

The left eye, on SPI-0, is wired as per:
  - DIN:   ->  Pin 19, GPIO 10    SPI_0 MOSI (Master Out Slave In)
  - CLK:   ->  Pin 23, GPIO 11    SPI_0 clock line
  -  CS:   ->  Pin 24, GPIO 8     SPI_0 CE0 (Chip Enable)
  -  DS:   ->  Pin 22, GPIO 25    Data or Command selection
  - RST:   ->  Pin 13, GPIO 27    Reset line for the display
#  -  BL:   ->  Pin 12, GPIO 18    Backlight control with PWM0
  -  BL:   ->  Pin 32, GPIO 12    Backlight control with PWM0

NOTE: This is how NOT how the manual requests it is conected to SPI_0.
      BL is moved to pin32

The right eye, on SPI-1, is wired as per:
  - DIN:   -> Pin 38, GPIO 20     SPI_1 MOSI (Master Out Slave In)
  - CLK:   -> Pin 40, GPIO 21     SPI_1 clock line
  - CS:    -> Pin 12, GPIO 18     SPI_1 CE0 (Chip Enable) [pi-4 specific]
  - DS:    -> Pin 37, GPIO 26     Data or Command selection
  - RST:   -> Pin 31, GPIO 6      Reset line for the display
  - BL:    -> Pin 33, GPIO 13     Backlight control with PWM1
"""
import math
import sys
import time
import logging
import numpy as np
import spidev
sys.path.append("..")
from lib import LCD_1inch28
from PIL import Image, ImageDraw, ImageChops
from eye_render import render_eye
from scipy.ndimage import label


def find_updated_regions(image1, image2, min_area):
    # Calculate the difference between the two images
    diff = ImageChops.difference(image1, image2)

    # Convert the difference image to a binary image
    diff_np = np.array(diff).astype(np.uint8)
    binary_diff = np.any(diff_np > 0, axis=-1)

    # Find connected components in the binary image
    labeled_diff, num_features = label(binary_diff)

    bounding_rectangles = []

    # Iterate through connected components and calculate their bounding rectangles
    for i in range(1, num_features + 1):
        component_mask = (labeled_diff == i)
        area = np.sum(component_mask)

        # Filter connected components based on the min_area parameter
        if area >= min_area:
            rows, cols = np.nonzero(component_mask)
            bounding_rect = (cols.min(), rows.min(), cols.max(), rows.max())
            bounding_rectangles.append(bounding_rect)

    return bounding_rectangles

def blit_window(disp: LCD_1inch28.LCD_1inch28,
                img_all: Image.Image,
                box):
    x, y, x2, y2 = box
    x, y, x2, y2 = int(x), int(y), int(x2), int(y2)

    # I'm getting some trails, nude this to make it bigger.
    x2, y2 = x2+1, y2+1
    x2, y2 = min(x2, disp.width), min(y2, disp.height)

    w, h = x2-x, y2-y
    # slice image to window
    img = np.asarray(img_all)
    img = img[y:y2, x:x2, :]

    # convert 3 bytes per pixel, to 2 bytes per pixel (65k) color
    pix = np.zeros((h, w, 2), dtype=np.uint8)
    pix[...,[0]] = np.add(np.bitwise_and(img[...,[0]],0xF8),np.right_shift(img[...,[1]],5))
    pix[...,[1]] = np.add(np.bitwise_and(np.left_shift(img[...,[1]],3),0xE0),np.right_shift(img[...,[2]],3))
    pix = pix.flatten().tolist()

    # Write window of buffer to physical display
    disp.SetWindows(x, y, x2, y2)
    disp.digital_write(disp.DC_PIN, disp.GPIO.HIGH)
    for i in range(0, len(pix), 4096):
        disp.spi_writebyte(pix[i:i+4096])



def main():
    pd = 10

    disp_left = LCD_1inch28.LCD_1inch28(bl=12)
    spi_1 = spidev.SpiDev(1, 0)
    display_right = LCD_1inch28.LCD_1inch28(spi=spi_1,
                           rst=6, dc=26, bl=13)

    img_buffers = [Image.new("RGB", (disp_left.width, disp_left.height), (0, 0, 0)) for _ in range(4)]
    draw_buffers = [ImageDraw.Draw(b) for b in img_buffers]
    # Initialize display.
    disp_left.Init()
    disp_left.clear()

    display_right.Init()
    display_right.clear()

    radius = 500
    start_time = time.time()
    frame: int = 0

    try:
        while True:
            idx_draw = frame % 2
            idx_last = (frame+1) % 2

            draw = draw_buffers[idx_draw]

            elapsed_time = time.time() - start_time
            speed = 1
            angle = 2 * math.pi * elapsed_time * speed
            # angle = 0
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            point_to_look_at = (x, y, 1_000)

            render_eye(draw, (disp_left.width, disp_left.height), -pd, point_to_look_at)

            bboxes = find_updated_regions(img_buffers[idx_last], img_buffers[idx_draw], 16)

            for box in bboxes:
                blit_window(disp_left, img_buffers[idx_draw], box)
                blit_window(display_right, img_buffers[idx_draw], box)

            # disp.ShowImage(img_buffers[idx_draw])

            #time.sleep(0.005)
            frame += 1

    except KeyboardInterrupt:
        print("Container shutdown.")
        disp_left.module_exit()
        display_right.module_exit()
        sys.exit(0)
    except IOError as e:
        logging.info(e)


if __name__ == '__main__':
    main()
