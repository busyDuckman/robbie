import numpy as np
import math
import time
from PIL import Image, ImageDraw

def centered_box(pos, r):
    x, y = pos
    return (x - r, y - r, x + r, y + r)



def render_eye_parts(image_size):
    w, h = image_size
    eye_radius = min(w, h) // 2
    pupil_radius = eye_radius // 4
    iris_radius = eye_radius // 2

    # eye
    eye = Image.new('RGBA', image_size, (0,0,0,0))
    draw = ImageDraw.Draw(eye)
    draw.ellipse(centered_box((w//2, h//2), eye_radius), fill=(255, 255, 255))

    # iris
    iris = Image.new('RGBA', (iris_radius*2, iris_radius*2), (0,0,0,0))
    draw = ImageDraw.Draw(iris)
    draw.ellipse(centered_box((iris_radius, iris_radius), iris_radius), fill=(0, 100, 255))

    # iris glint
    iris_glint = Image.new('RGBA', (iris_radius*2, iris_radius*2), (0,0,0,0))
    draw = ImageDraw.Draw(iris_glint)
    draw.pieslice(centered_box((iris_radius, iris_radius), iris_radius), 240 - 15, 240 + 15, fill=(255, 255, 255))

    # pupil
    pupil = Image.new('RGBA', (pupil_radius*2, pupil_radius*2), (0,0,0,0))
    draw = ImageDraw.Draw(pupil)
    draw.ellipse(centered_box((pupil_radius, pupil_radius), pupil_radius), fill=(0, 0, 0))

    # pupil glint
    pupil_glint = Image.new('RGBA', (pupil_radius*2, pupil_radius*2), (0,0,0,0))
    draw = ImageDraw.Draw(pupil_glint)
    draw.pieslice(centered_box((pupil_radius, pupil_radius), pupil_radius), 240 - 15, 240 + 15, fill=(255, 255, 255))

    return eye, iris, iris_glint, pupil, pupil_glint


















def render_eye(draw: ImageDraw.Draw,
               image_size,
               pd,
               point_to_look_at):
    """
    An eye rendered to the size of an image.
    :param pd: The distance of the eye from the center of the face (mm).
               Used for calculating where the eye is looking.
               For two eyes 20cm apart, you would call this function
               twice with pd set to -10 and +10.
    :param point_to_look_at: A 3d point the eyes are focused on (mm).
              +x makes the eyes look to the right
              -x makes them look left
              +y makes them look up
              -y looking down
              0 <= z < inf
              a small value of z makes the eyes go cross-eyed.

    :param image_size: Output Image Size.
    :return:
    """
    w, h = image_size
    eye_radius = min(w, h) // 2
    pupil_radius = eye_radius// 4
    iris_radius = eye_radius// 2

    eye_center = (w//2, h//2)
    # img = Image.new('RGB', image_size, (0,0,0))
    # draw = ImageDraw.Draw(img)

    # Clear the image
    # draw.rectangle([0, 0, w, h], fill=(0, 0, 0))

    # Draw eye outline
    # eye_box = centered_box(eye_center, eye_radius)
    # draw.ellipse(eye_box,
    #              fill=(255, 255, 255), outline=(0, 0, 0))

    # why not just memset the whole thing white, it's a round display after all.
    draw.rectangle([0, 0, w, h], fill=(255, 255, 255))

    # Calculate the gaze direction
    dx = point_to_look_at[0] - pd
    dy = point_to_look_at[1]
    dz = point_to_look_at[2]
    distance = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)

    # Normalize direction vector
    dx /= distance
    dy /= distance
    dz /= distance

    # Calculate pupil/iris position in 2D image coordinates
    iris_x = eye_center[0] + int(dx * (eye_radius - pupil_radius))
    iris_y = eye_center[1] + int(dy * (eye_radius - pupil_radius))

    # nudge the pupil a bit to create a 3d effect.
    pupil_x = eye_center[0] + int(dx * 1.2 * (eye_radius - pupil_radius))
    pupil_y = eye_center[1] + int(dy * 1.2 * (eye_radius - pupil_radius))

    # that shiny glint from the light
    light_angle = 240
    la_start = light_angle - 15
    la_end = light_angle + 15

    iris_col = (0, 100, 255)
    pupil_col = (0, 0, 0)

    # Draw iris
    iris_box = centered_box((iris_x, iris_y), iris_radius)
    draw.ellipse(iris_box, fill=iris_col)

    # glint in the iris
    iris_glint_box = centered_box((pupil_x, pupil_y), iris_radius * 0.8)
    draw.pieslice(iris_glint_box, la_start, la_end, fill=(255, 255, 255))

    # redraw part of the iris over th glint
    mini_iris_box = centered_box((pupil_x, pupil_y), pupil_radius*1.2)
    draw.ellipse(mini_iris_box, fill=iris_col)

    # Draw pupil
    pupil_box = centered_box((pupil_x, pupil_y), pupil_radius)
    draw.ellipse(pupil_box, fill=(0, 0, 0))

    # glint in the pupil
    pupil_glint_box = centered_box((pupil_x, pupil_y), pupil_radius * 0.75)
    draw.pieslice(pupil_glint_box, la_start, la_end, fill=(255, 255, 255))

    # redraw part of the pupil over th glint
    mini_pupil_box = centered_box((pupil_x, pupil_y), pupil_radius * 0.4)
    draw.ellipse(mini_pupil_box, fill=pupil_col)



# -----------------------------------------------------------------------------


def animate_eye(pd, radius=500, image_size=(256, 256)):
    import cv2
    window_name = "Eye Animation"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, *image_size)

    start_time = time.time()

    image_size = (256, 256)
    img = Image.new('RGB', image_size, (0, 0, 0))
    draw = ImageDraw.Draw(img)

    while True:
        elapsed_time = time.time() - start_time
        speed = 1
        angle = 2 * math.pi * elapsed_time * speed
        # angle = 0
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        point_to_look_at = (x, y, 1_000)

        render_eye(draw, image_size, pd, point_to_look_at)
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        cv2.imshow(window_name, frame)

        key = cv2.waitKey(18) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    animate_eye(-10)
