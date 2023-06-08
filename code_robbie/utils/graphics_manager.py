import os.path

import cv2
import numpy as np
from PIL import Image, ImageChops
from scipy.ndimage import label

from utils.updated_region_finder import RegionAlg


def _pre_mul_alpha_rgba(img):
    """
    This takes an image and creates:
        A premultiplied alpha [R,G,B]
        A 1-alpha mask as [a,a,a].
    :param img:
    :return:
    """
    alpha = img[:, :, 3] / 255.0
    alpha_rgb = np.repeat(alpha[:, :, np.newaxis], 3, axis=2)
    premult_img = cv2.convertScaleAbs(img[:, :, :3] * alpha_rgb)
    return premult_img, 1 - alpha_rgb


def _pre_mul_alpha_rgb_and_a(img, alpha):
    """
    This takes an image and creates:
        A premultiplied alpha [R,G,B]
        A 1-alpha mask as [a,a,a].
    :param img:
    :return:
    """
    alpha = alpha / 255.0
    alpha_rgb = np.repeat(alpha[:, :, np.newaxis], 3, axis=2)
    premult_img = cv2.convertScaleAbs(img[:, :, :3] * alpha_rgb)
    return premult_img, 1 - alpha_rgb


def rescale_img(img, scale):
    # get the original image dimensions
    original_height, original_width = img.shape[:2]

    # calculate the new dimensions
    new_width = max(1, int(original_width * scale))
    new_height = max(1, int(original_height * scale))

    # resize the image
    resized_img = cv2.resize(img, (new_width, new_height))

    return resized_img


class Sprite:
    """
      This is the image format used for realtime rendering.

      The format is a BGR image with premultiplied alpha channel.
      """

    _internal_format: str = "RGB"  # NO ALPHA

    def __init__(self, img, fmt: str = "RGBA", strip_alpha=False):
        """
        Creates a new interlaced Image.
        If the image has an alpha channel to will be removed and the other channels premultiplied.
        :param img: An image of type: list, numpy or PIL Image
        :param fmt: If not a PIL Image, A format string. 4 valid chars:  A, R, G, B. A is optional.
        """
        self.width: int = None
        self.height: int = None
        self.alpha_composite: bool = None
        self.image: np.ndarray = None
        self.alpha_image: np.ndarray = None

        # load a file, if given a string
        if isinstance(img, str):
            if not os.path.isfile(img):
                raise FileNotFoundError(img)
            try:
                img = cv2.imread(img, cv2.IMREAD_UNCHANGED)
            except Exception as e:
                raise ValueError("unable to load file: " + img, + " error: " + str(e))

        # sort out the data we got
        if isinstance(img, Image.Image):
            img = np.array(img)
            # TODO: inspect image format and set fmt to match
            fmt = img.mode
            self.alpha_composite = "A" in fmt.upper()
        else:
            if isinstance(img, list):
                img = np.array(img)

            if not isinstance(img, np.ndarray):
                raise TypeError("img is expected to be: PIL, numpy or list.")

        # validate fmt string, and get metadata
        fmt = fmt.upper().replace(" ", "").replace(",", "").strip()
        fmt_test = "".join(sorted(set(fmt)))
        if fmt_test not in ["ABGR", "BGR"]:
            raise ValueError("Invalid image format string.")
        self.alpha_composite = "A" in fmt  # Controls how this image is composed onto another.

        # validate the image, and get metadata
        if len(img.shape) != 3:
            raise ValueError("Image not x, by y, by depth.")
        if img.shape[2] != len(fmt):
            raise ValueError(f"Image color depth {img.shape[3]} does not match format {fmt}.")
        self.height, self.width = img.shape[:2]

        # get channels via the fmt string
        channels = {channel: img[:, :, i] for i, channel in enumerate(fmt)}

        # compose to native format (without alpha)
        this_fmt = Sprite._internal_format
        self.image = cv2.merge([channels[char] for char in this_fmt])

        if strip_alpha:
            self.alpha_composite = False
        else:
            # apply alpha pre-multiplication
            alpha = channels.get("A")
            self.image, self.alpha_image = _pre_mul_alpha_rgb_and_a(self.image, alpha)

    def __str__(self):
        return f"Sprite(w={self.width}, h={self.height}, a={self.alpha_composite})"


class Composer:
    """
    This handles composing images from sprites, and
    provides elementary drawing primitives.

    The composer supports double buffering and algorithms to
    segment and mark regions changed since the last frame.
    """
    def __init__(self, w, h):
        """
        Creates a new canvas for rendering interlaced graphics.
        :param w: Width.
        :param h: Height, can be odd that won't upset anything.
        """
        self.width = w
        self.height = h
        self.buffers = [np.zeros((h, w, 4), dtype=np.uint8)
                        for _ in range(2)]
        self.frame: int = 0
        self.draw_buffer = self.buffers[self.frame % 2]
        self.render_buffer = self.buffers[(self.frame + 1) % 2]



    def get_native_sprite(self, source) -> Sprite:
        return Sprite(source)

    def next_frame(self) -> bool:
        """
        Advances to the next draw buffer.
        :return: True for even frames.
        """
        self.frame += 1
        self.draw_buffer = self.buffers[self.frame % 2]
        self.render_buffer = self.buffers[(self.frame+1) % 2]
        even_scan = not (self.frame % 2)
        return even_scan

    def clear_screen(self) -> None:
        """
        Clears the current draw buffer.
        """
        self.draw_buffer[...] = 0

    def draw_sprite(self, sprite: Sprite, x, y) -> None:
        """
        Pastes a sprite at x, y.
        Only the necessary rows will be copied to the draw buffer.

        :param img: Image to paste.
        :param x: Position of top of img.
        :param y: Position of left of img.
        :return:
        """
        img = sprite.image
        alpha = sprite.alpha_image
        end_y = y + sprite.height

        try:
            if sprite.alpha_composite:
                # We need to combine the image with the existing image in the draw buffer
                # using alpha blending.

                # the test_sprite.py way
                # roi = render_buffer[sp_y:sp_y + sp_height, sp_x:sp_x + sp_width]
                # render_buffer[sp_y:sp_y + sp_height, sp_x:sp_x + sp_width] = \
                #     cv2.convertScaleAbs(sp_image[:, :, :3] + roi * sp_alpha_inv)

                # roi = self.draw_buffer[y:end_y, x:x + sprite.width]  # 3 byte pixels
                roi = self.draw_buffer[y:end_y, x:x + sprite.width, :3]   # 4 byte pixels
                np.add(img[:, :, :3], roi * alpha, out=roi, casting="unsafe")
            else:
                # We simply replace the image in the draw buffer with the new image.
                self.draw_buffer[y:end_y, x:x + sprite.height] = img
        except ValueError as e:
            print(f"error @ draw_sprite({sprite}, {x}, {y}): {e}")
            raise e

    def find_dirty_recs(self, algorithm: RegionAlg):
        return algorithm(self.render_buffer, self.draw_buffer)

    def __str__(self):
        return f"{self.__class__.__name__} {self.width}x{self.height}"


def generate_debug_image(img, boxes):
    # Define color LUT
    col_lut = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    # 3 channel gray scale.
    gray_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_image = cv2.cvtColor(gray_image, cv2.COLOR_GRAY2BGR)

    # colour in every box
    overlay = gray_image.copy()

    for i, box in enumerate(boxes):
        x1, y1, x2, y2 = box
        color = col_lut[i % len(col_lut)]
        # That's not my rectangle, its edges are too fuzzy.
        # cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        overlay[y1:y2, x1:x2] = color

    dbg_image = cv2.addWeighted(overlay, 0.5, gray_image, 0.5, 0)

    return dbg_image



