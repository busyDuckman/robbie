import cv2
import numpy as np
from PIL import Image, ImageDraw
from math import sin, cos, radians, sqrt

from eye_manager.interlaced_graphics_manager import InterlacedComposer, InterlacedImage
from utils.fps_counter import FPSCounter


def paste_via_alpha_blending(canvas_img, img, pos_x, pos_y):
    # Create an ROI of the same size as img
    rows, cols, _ = img.shape
    roi = canvas_img[pos_y:pos_y+rows, pos_x:pos_x+cols]

    img_bgr = img[:, :, :3]
    img_a = img[:, :, 3]

    # Normalize the alpha image to have values between 0 and 1.
    img_a = cv2.normalize(img_a, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)

    # Blend the ROI with img_bgr.
    blended = roi * (1 - img_a[:, :, None]) + img_bgr * img_a[:, :, None]

    # Insert the ROI back into the canvas.
    canvas_img[pos_y:pos_y+rows, pos_x:pos_x+cols] = blended

def paste_via_alpha_blending_premultiplied(canvas_img, img, pos_x, pos_y):
    # Create an ROI of the same size as img in canvas_img.
    rows, cols, _ = img.shape

    canvas_img[pos_y:pos_y + rows, pos_x:pos_x + cols] += img

    # roi = canvas_img[pos_y:pos_y+rows, pos_x:pos_x+cols]
    # canvas_img[pos_y:pos_y + rows, pos_x:pos_x + cols] = roi + img

    # result = cv2.add(roi, img)
    # canvas_img[pos_y:pos_y + rows, pos_x:pos_x + cols] = result


def pre_mul_alpha(img):
    img_rgb = img[:, :, :3]
    img_a = img[:, :, 3, np.newaxis]
    return (img_rgb * (img_a / 255.0)).astype(np.uint8)


def centered_box(pos, r):
    x, y = pos
    return (x - r, y - r, x + r, y + r)


class EyeRenderer:
    def __init__(self, w, h,
                 eye_color = (255, 255, 255),
                 pupil_color = (0, 100, 255),
                 iris_color = (0, 0, 0)):
        self.w = w
        self.h = h
        self.image_size = (w, h)
        self.eye_center = (w // 2, h // 2)

        self.eye_radius = min(w, h) // 2
        self.pupil_radius = self.eye_radius // 4
        self.iris_radius = self.eye_radius // 2

        self.iris_color = iris_color
        self.pupil_color = pupil_color
        self.eye_color = eye_color

        # that shiny glint from the light
        self.light_angle = 240
        self.la_start = self.light_angle - 15
        self.la_end = self.light_angle + 15

        # Note:
        # iris is a circle with a glint going al the way to the
        # centre of the pupil. To produce a simple 3d effect, the iris can
        # move when the eye is turned, it's not at the center of the pupil.

        img = self._render_eye_pil()
        self.img_eye_cv = cv2.cvtColor(np.array(img, dtype=np.uint8), cv2.COLOR_RGBA2BGRA)

        self.glint_cache = self._precalculate_glint_images(3, self.iris_radius)

        img = self._render_pupil_pil()
        self.img_pupil_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)

        img = self._render_iris_pil()
        self.img_iris_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)

        # interlaced versions
        self.img_eye_int = InterlacedImage(self.img_eye_cv, strip_alpha=True)
        self.img_iris_int = InterlacedImage(self.img_iris_cv)
        self.img_pupil_int = InterlacedImage(self.img_pupil_cv)

    def _precalculate_glint_images(self, min_radius, max_radius, step=1):
        """
        :return:  {min_radius: (img, cx, cy), ... min_radius: (img, cx, cy)}
        """
        glint_images = {}
        mem_usage = 0
        for radius in range(min_radius, max_radius + 1, step):
            img, x_centre, y_centre = self._render_glint(radius)
            mem_usage += img.width * img.height * 4
            glint_images[radius] = (cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA), x_centre, y_centre)

        print(f"Glint cache mem usage: {mem_usage//(1024)}kB")
        return glint_images


    def _render_glint(self, radius) -> Image.Image:
        """
        Draw a pie slice and return it as: (img, x_centre, y_centre)
        eg:
          - img, x_centre, y_centre = render_glint(20)
          - to draw the glin focused at x, y, use (x - x_centre, y-y_centre) as
            the point to position the top left of img.
        """
        # TODO: create the smallest possible width and height that will
        #       hold the pie slice, and determine x_centre, y_centre.
        #       To find this, self.la_start, self.la_end are the size
        #       of the pie slice.

        la_start, la_end = self.la_start, self.la_end

        # Calculate the points on the circle for the start and end angles
        x1 = radius * cos(radians(la_start))
        y1 = radius * sin(radians(la_start))
        x2 = radius * cos(radians(la_end))
        y2 = radius * sin(radians(la_end))

        # The center of the circle is also a point of interest
        points = [(0, 0), (x1, y1), (x2, y2)]

        # Check if the angles cross the x or y axis and add the points at the extremities
        if la_start <= 0 <= la_end or la_start <= 180 <= la_end:
            points.append((radius, 0))
        if la_start <= 90 <= la_end or la_start <= 270 <= la_end:
            points.append((0, radius))
        if la_start <= 180 <= la_end or la_start <= 360 <= la_end:
            points.append((-radius, 0))
        if la_start <= 270 <= la_end or la_start <= 90 <= la_end:
            points.append((0, -radius))

        # Calculate the bounding box around the points
        min_x = min(x for x, y in points)
        max_x = max(x for x, y in points)
        min_y = min(y for x, y in points)
        max_y = max(y for x, y in points)

        # Calculate the dimensions of the bounding box and the center point
        width = int(max_x - min_x)
        height = int(max_y - min_y)
        x_centre = int(-min_x)
        y_centre = int(-min_y)

        # Render
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        iris_glint_box = centered_box((x_centre, y_centre), radius)
        draw.pieslice(iris_glint_box, la_start, la_end, fill=(255, 255, 255, 255))

        return img, x_centre, y_centre

    def _render_iris_pil(self) -> Image.Image:
        iris_radius = self.iris_radius
        img = Image.new('RGBA', (iris_radius * 2+1, iris_radius * 2+1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse(centered_box((iris_radius, iris_radius), iris_radius), fill=(0, 100, 255))
        return img

    def _render_pupil_pil(self) -> Image.Image:
        pupil_radius = self.pupil_radius
        total_radius = int(pupil_radius * 1.2)
        mini_iris_box = centered_box((total_radius, total_radius), total_radius)

        img = Image.new('RGBA', (total_radius * 2+1, total_radius * 2+1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # first we draw some glint free iris, to go over the glint in the iris
        draw.ellipse(mini_iris_box, fill=self.pupil_color)
        draw.ellipse(centered_box((total_radius, total_radius), pupil_radius), fill=(0, 0, 0))
        return img

    def _render_eye_pil(self) -> Image.Image:
        w, h, eye_radius = self.w, self.h, self.eye_radius

        img = Image.new('RGBA', self.image_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse(centered_box((w // 2, h // 2), eye_radius), fill=(255, 255, 255))
        return img

    def calc_gaze_direction(self, pd, point_to_look_at):
        # Calculate the gaze direction
        dx = point_to_look_at[0] - pd
        dy = point_to_look_at[1]
        dz = point_to_look_at[2]
        distance = sqrt(dx ** 2 + dy ** 2 + dz ** 2)

        # Normalize direction vector
        dx /= distance
        dy /= distance
        dz /= distance

        return dx, dy, dz

    def compose_eye(self, pd, point_to_look_at, dest_buffer) -> None:
        dx, dy, dz = self.calc_gaze_direction(pd, point_to_look_at)

        # Calculate pupil/iris position in 2D image coordinates
        eye_center, eye_radius = self.eye_center, self.eye_radius
        pupil_radius = self.pupil_radius

        iris_x = eye_center[0] + int(dx * (eye_radius - pupil_radius))
        iris_y = eye_center[1] + int(dy * (eye_radius - pupil_radius))

        # nudge the pupil a bit to create a 3d effect.
        pupil_x = eye_center[0] + int(dx * 1.2 * (eye_radius - pupil_radius))
        pupil_y = eye_center[1] + int(dy * 1.2 * (eye_radius - pupil_radius))

        np.copyto(dest_buffer, pre_mul_alpha(self.img_eye_cv))

        # draw iris
        x, y = iris_x - self.iris_radius, iris_y - self.iris_radius
        paste_via_alpha_blending(dest_buffer, self.img_iris_cv, x, y)
        # paste_via_alpha_blending_premultiplied(dest_buffer, pre_mul_alpha(self.img_iris_cv), x, y)

        # glint in the iris
        glint_radius = int(self.iris_radius * 0.8)
        img, gx, gy = self.glint_cache[glint_radius]
        # x, y = pupil_x-glint_radius-gx, pupil_y-glint_radius-gy
        x = pupil_x - gx
        y = pupil_y - gy
        paste_via_alpha_blending(dest_buffer, img, x, y)

        w = self.img_pupil_cv.shape[0]
        h = self.img_pupil_cv.shape[1]
        x = pupil_x - w // 2
        y = pupil_y - h // 2
        paste_via_alpha_blending(dest_buffer, self.img_pupil_cv, x, y)

    def compose_eye_interlaced(self, pd, point_to_look_at, canvas: InterlacedComposer):
        dx, dy, dz = self.calc_gaze_direction(pd, point_to_look_at)

        # Calculate pupil/iris position in 2D image coordinates
        eye_center, eye_radius = self.eye_center, self.eye_radius
        pupil_radius = self.pupil_radius

        iris_x = eye_center[0] + int(dx * (eye_radius - pupil_radius))
        iris_y = eye_center[1] + int(dy * (eye_radius - pupil_radius))

        # nudge the pupil a bit to create a 3d effect.
        pupil_x = eye_center[0] + int(dx * 1.2 * (eye_radius - pupil_radius))
        pupil_y = eye_center[1] + int(dy * 1.2 * (eye_radius - pupil_radius))

        # np.copyto(dest_buffer, pre_mul_alpha(self.img_eye_cv))
        canvas.clear_screen()
        canvas.paste_image(self.img_eye_int, 0, 0)

        # draw iris
        x, y = iris_x - self.iris_radius, iris_y - self.iris_radius
        canvas.paste_image(self.img_iris_int, x, y)
        # paste_via_alpha_blending(dest_buffer, self.img_iris_cv, x, y)
        # # paste_via_alpha_blending_premultiplied(dest_buffer, pre_mul_alpha(self.img_iris_cv), x, y)

        # # glint in the iris
        # glint_radius = int(self.iris_radius * 0.8)
        # img, gx, gy = self.glint_cache[glint_radius]
        # # x, y = pupil_x-glint_radius-gx, pupil_y-glint_radius-gy
        # x = pupil_x - gx
        # y = pupil_y - gy
        # paste_via_alpha_blending(dest_buffer, img, x, y)
        #
        # w = self.img_pupil_cv.shape[0]
        # h = self.img_pupil_cv.shape[1]
        # x = pupil_x - w // 2
        # y = pupil_y - h // 2
        # paste_via_alpha_blending(dest_buffer, self.img_pupil_cv, x, y)




def test_animate_eye(pd, radius=500, image_size=(240, 240)):
    """
    Shows the eye on a PC for testing purposes
    """
    import time
    import math

    window_name = "Eye Animation"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, *image_size)

    start_time = time.time()

    w, h = image_size
    buffer = np.zeros((w, h, 3), dtype=np.uint8)

    eye_renderer = EyeRenderer(240, 240)

    while True:
        elapsed_time = time.time() - start_time
        speed = 1

        angle = 2 * math.pi * elapsed_time * speed
        # angle = 0
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        point_to_look_at = (x, y, 1_000)

        eye_renderer.compose_eye(pd, point_to_look_at, buffer)

        # frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        cv2.imshow(window_name, buffer)

        key = cv2.waitKey(18) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()

def test_animate_eye_interlaced(pd, radius=500, image_size=(240, 240)):
    """
    Shows the eye on a PC for testing purposes
    """
    import time
    import math

    window_name = "Eye Animation"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, *image_size)

    start_time = time.time()

    w, h = image_size
    buffer = np.zeros((w, h, 3), dtype=np.uint8)

    eye_renderer = EyeRenderer(240, 240)
    composer = InterlacedComposer(240, 240)

    fps = FPSCounter(update_interval=5)

    while True:
        if fps.update():
            print("  - current fps =", fps)

        elapsed_time = time.time() - start_time
        speed = 1

        angle = 2 * math.pi * elapsed_time * speed
        # angle = 0
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        point_to_look_at = (x, y, 1_000)

        # eye_renderer.compose_eye(pd, point_to_look_at, buffer)
        eye_renderer.compose_eye_interlaced(pd, point_to_look_at, composer)

        # frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        # buffer[...] = 0
        composer.render_test_rows(buffer)
        cv2.imshow(window_name, buffer)
        composer.next_frame()

        key = cv2.waitKey(6) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    test_animate_eye_interlaced(-10)