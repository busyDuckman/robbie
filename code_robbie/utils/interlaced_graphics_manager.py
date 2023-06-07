import numpy as np
import cv2
from PIL import Image

from utils.graphics_manager import Sprite, Composer, _pre_mul_alpha_rgb_and_a


class InterlacedSprite(Sprite):
    """
    This is the image format used for realtime rendering.
    We are running an interlaced display, and as such only need
    to composite alternate lines. This class supports that effort.

    The format is two BGR images with premultiplied alpha channel.
    """

    _internal_format: str = "RGB"  # NO ALPHA
    def __init__(self, img, fmt: str = "RGBA", strip_alpha=False):
        """
        Creates a new interlaced Image.
        If the image has an alpha channel to will be removed and the other channels premultiplied.
        :param img: An image of type: list, numpy or PIL Image
        :param fmt: If not a PIL Image, A format string. 4 valid chars:  A, R, G, B. A is optional.
        """
        img_np = None
        img_a = None
        self.width = None
        self.height = None
        if isinstance(img, Image.Image):
            img_np = np.array(img)
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
        this_fmt = InterlacedSprite._internal_format
        native_img = cv2.merge([channels[char] for char in this_fmt])

        if strip_alpha:
            self.alpha_composite = False
            self.even_rows_alpha = None
            self.odd_rows_alpha = None
        else:
            # apply alpha pre-multiplication
            alpha = channels.get("A")
            native_img, alpha = _pre_mul_alpha_rgb_and_a(native_img, alpha)
            self.even_rows_alpha = alpha[::2]
            self.odd_rows_alpha = alpha[1::2]

        # spit the channels
        self.even_rows = native_img[::2]
        self.odd_rows = native_img[1::2]


        # extra meta data
        self.num_odd_rows = self.height // 2
        self.num_even_rows = self.height - self.num_odd_rows

    def __str__(self):
        return f"InterlacedSprite(w={self.width}, h={self.height}, a={self.alpha_composite})"

    def resolve(self, y, even_scan):
        if not even_scan:
            y += 1
        if y % 2 == 0:
            return self.even_rows
        return self.odd_rows

    def resolve_alpha(self, y, even_scan):
        if not even_scan:
            y += 1
        if y % 2 == 0:
            return self.even_rows_alpha
        return self.odd_rows_alpha


class InterlacedComposer(Composer):
    """
    This handles composing images that are interlaced and double buffered.
    To save on system resources, only odd or even rows are composed in
    the canvas at any time.

    The double buffering is to assist with reducing SPI bus bandwidth.
    The previous buffer recalls the last frame allowing only the difference
    of the scanline to be transmitted.

    This class can compose images of type InterlacedImage, that are already
    seperated into odd and even rows.
    """
    def __init__(self, w, h):
        """
        Creates a new canvas for rendering interlaced graphics.
        :param w: Width.
        :param h: Height, can be odd that won't upset anything.
        """
        super().__init__(w, h)

        self.num_odd_rows = h // 2
        self.num_even_rows = h - self.num_odd_rows
        self.odd_buffers = [np.zeros((self.num_odd_rows, w, 3), dtype=np.uint8)
                            for _ in range(2)]
        self.even_buffers = [np.zeros((self.num_even_rows, w, 3), dtype=np.uint8)
                             for _ in range(2)]
        self.buffers = [self.even_buffers[0], self.odd_buffers[0],
                        self.even_buffers[1], self.odd_buffers[1]]
        self.frame: int = 0
        self.draw_buffer = self.even_buffers[0]
        self.render_buffer = self.even_buffers[1]
        # self.current_rows = self.num_even_rows
        self.even_scan = True

    def next_frame(self) -> bool:
        """
        Advances to the next draw buffer.
        :return: True if the new frame is for an even scan line draw.
        """
        self.frame += 1
        self.draw_buffer = self.buffers[self.frame % 4]
        self.render_buffer = self.buffers[(self.frame+2) % 4]
        # self.current_rows = self.num_even_rows
        # if self.frame % 2:
        #     self.current_rows = self.num_odd_rows
        self.even_scan = not (self.frame % 2)
        return self.even_scan

    def clear_screen(self) -> None:
        """
        Clears the current draw buffer.
        :return:
        """
        self.draw_buffer[...] = 0

    def draw_sprite(self, img: InterlacedSprite, x, y) -> None:
        """
        Pastes a InterlacedImage at x, y.
        Only the necessary rows will be copied to the draw buffer.

        :param img: Image to paste.
        :param x: Position of top of img.
        :param y: Position of left of img.
        :return:
        """
        img_rows = img.resolve(y, self.even_scan)
        start_y = (y + int(not self.even_scan)) // 2
        end_y = start_y + img_rows.shape[0]

        try:
            if img.alpha_composite:
                # We need to combine the image with the existing image in the draw buffer
                # using alpha blending.
                # self.draw_buffer[start_y:end_y, x:x + img.width] = cv2.addWeighted(
                #     self.draw_buffer[start_y:end_y, x:x + img.width], 1 - img_rows, img_rows, 1, 0
                # )
                alpha_rows = img.resolve_alpha(y, self.even_scan)
                roi = self.draw_buffer[start_y:end_y, x:x + img.width]
                np.add(img_rows[:, :, :3], roi * alpha_rows, out=roi, casting="unsafe")
            else:
                # We simply replace the image in the draw buffer with the new image.
                self.draw_buffer[start_y:end_y, x:x + img.width] = img_rows
        except ValueError as e:
            print(f"paste({img}, {x}, {y})")
            raise e


    def render_test_rows(self, buffer: np.ndarray) -> None:
        """
        Renders the current rows to a buffer image for testing purposes.
        The buffer is the full images size and only half its rows will
        be altered.
        :param buffer: np image, exact size of this canvas.
        """
        if self.even_scan:
            buffer[::2] = self.draw_buffer
        else:
            buffer[1::2] = self.draw_buffer

    def get_native_sprite(self, source) -> Sprite:
        return InterlacedSprite(source)
