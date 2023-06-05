import random

import cv2
import numpy as np
import glob

from utils.fps_counter import FPSCounter


def pre_mul_alpha(img):
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


def pre_mul_alpha_3(img):
    alpha = img[:, :, 3] / 255.0
    alpha_rgb = np.repeat(alpha[:, :, np.newaxis], 3, axis=2)
    premult_img = cv2.convertScaleAbs(img[:, :, :3] * alpha_rgb)
    alpha_inv = (1 - alpha) * 255
    return np.dstack((premult_img, alpha_inv))


def rescale_img(img, scale):
    # get the original image dimensions
    original_height, original_width = img.shape[:2]

    # calculate the new dimensions
    new_width = max(1, int(original_width * scale))
    new_height = max(1, int(original_height * scale))

    # resize the image
    resized_img = cv2.resize(img, (new_width, new_height))

    return resized_img


def load_sprites_3(bg_image, multiply=1):
    sprites_data = []
    adj = [1.1, 1.2, 1.05, -1.1, -1.2, -1.1, 1.5, 1.3, -1.5, -1.3]
    for q, filename in enumerate(glob.glob(r'C:\temp\dbx_sprite_*.png')):
        sprite_image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        sprite_image = rescale_img(sprite_image, 0.3)
        sprite_image = pre_mul_alpha_3(sprite_image)

        for z in range(multiply):
            sprite_data = {
                'image': sprite_image,
                # 'alpha_inv': alpha_inv,
                'x': (128 + random.randint(0, 512)) % (bg_image.shape[1] - sprite_image.shape[1] - 1),
                'y': (256 + random.randint(0, 512)) % (bg_image.shape[0] - sprite_image.shape[0] - 1),
                'dx': random.random() * 4 - 2,
                'dy': random.random() * 4 - 2,
            }
            # print(sprite_data)
            sprites_data.append(sprite_data)
    random.shuffle(sprites_data)
    return sprites_data

def load_sprites(bg_image, multiply=1):
    sprites_data = []
    adj = [1.1, 1.2, 1.05, -1.1, -1.2, -1.1, 1.5, 1.3, -1.5, -1.3]
    for q, filename in enumerate(glob.glob(r'C:\temp\dbx_sprite_*.png')):
        sprite_image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        sprite_image = rescale_img(sprite_image, 0.3)
        sprite_image, alpha_inv = pre_mul_alpha(sprite_image)

        for z in range(multiply):
            sprite_data = {
                'image': sprite_image,
                'alpha_inv': alpha_inv,
                'x': (128 + random.randint(0, 512)) % (bg_image.shape[1] - sprite_image.shape[1] - 1),
                'y': (256 + random.randint(0, 512)) % (bg_image.shape[0] - sprite_image.shape[0] - 1),
                'dx': random.random() * 4 - 2,
                'dy': random.random() * 4 - 2,
            }
            # print(sprite_data)
            sprites_data.append(sprite_data)
    random.shuffle(sprites_data)
    return sprites_data


def main():
    # load background (RGB) and sprite images
    bg_image = cv2.imread(r'c:\temp\lenna.png')
    
    # Initialize the sprites data
    sprites_data = load_sprites(bg_image, multiply=50)

    print(f"{len(sprites_data)} sprites loaded.")

    fps = FPSCounter(update_interval=0.5)
    render_buffer = np.zeros_like(bg_image, dtype=np.uint8)
    while True:
        if fps.update():
            print("  - current fps =", fps)

        np.copyto(render_buffer, bg_image)
        for sprite_data in sprites_data:
            # extract sprite data into variables for readability
            sp_x, sp_y, sp_dx, sp_dy = [sprite_data[q] for q in ['x','y','dx','dy']]
            sp_image, sp_alpha_inv = sprite_data['image'], sprite_data['alpha_inv']
            sp_height, sp_width = sp_image.shape[:2]

            # make (x, y, dx, dy) change like a box bouncing around the screen
            if sp_x + sp_width + sp_dx > bg_image.shape[1] or sp_x + sp_dx < 0:
                sp_dx = -sp_dx
            if sp_y + sp_height + sp_dy > bg_image.shape[0] or sp_y + sp_dy < 0:
                sp_dy = -sp_dy
            sp_x, sp_y = sp_x + sp_dx, sp_y + sp_dy

            # update sprites
            sprite_data['x'], sprite_data['y'] = sp_x, sp_y
            sprite_data['dx'], sprite_data['dy'] = sp_dx, sp_dy

            sp_x, sp_y = int(sp_x), int(sp_y)

            # blit fg_sprite to at x, y
            roi = render_buffer[sp_y:sp_y + sp_height, sp_x:sp_x + sp_width]
            render_buffer[sp_y:sp_y + sp_height, sp_x:sp_x + sp_width] = \
                cv2.convertScaleAbs(sp_image[:, :, :3] + roi * sp_alpha_inv)
        # Display the image
        cv2.imshow(f'{len(sprites_data)} Sprites', render_buffer)
    
        # exit on any key
        key = cv2.waitKey(1) & 0xFF
        if key != 255:
            break
    
    cv2.destroyAllWindows()


def main_2():
    # load background (RGB) and sprite images
    bg_image = cv2.imread(r'c:\temp\lenna.png')

    # Initialize the sprites data
    sprites_data = load_sprites(bg_image, multiply=50)

    print(f"{len(sprites_data)} sprites loaded.")

    fps = FPSCounter(update_interval=0.5)
    render_buffer = np.zeros_like(bg_image, dtype=np.uint8)
    while True:
        if fps.update():
            print("  - current fps =", fps)

        np.copyto(render_buffer, bg_image)
        for sprite_data in sprites_data:
            # extract sprite data into variables for readability
            sp_x, sp_y, sp_dx, sp_dy = [sprite_data[q] for q in ['x', 'y', 'dx', 'dy']]
            sp_image, sp_alpha_inv = sprite_data['image'], sprite_data['alpha_inv']

            # make (x, y, dx, dy) change like a box bouncing around the screen
            if sp_x + sp_image.shape[1] + sp_dx > bg_image.shape[1] or sp_x + sp_dx < 0:
                sp_dx = -sp_dx
            if sp_y + sp_image.shape[0] + sp_dy > bg_image.shape[0] or sp_y + sp_dy < 0:
                sp_dy = -sp_dy

            # update sprite positions
            sp_x += sp_dx
            sp_y += sp_dy
            sprite_data['x'], sprite_data['y'] = sp_x, sp_y
            sprite_data['dx'], sprite_data['dy'] = sp_dx, sp_dy

            sp_x, sp_y = int(sp_x), int(sp_y)

            # blit fg_sprite to at x, y
            roi = render_buffer[sp_y:sp_y + sp_image.shape[0], sp_x:sp_x + sp_image.shape[1]]
            np.add(sp_image[:, :, :3], roi * sp_alpha_inv, out=roi, casting="unsafe")
        # convert render_buffer to 8-bit image
        render_buffer = cv2.convertScaleAbs(render_buffer)

        # Display the image
        cv2.imshow(f'{len(sprites_data)} Sprites', render_buffer)

        # exit on any key
        key = cv2.waitKey(1) & 0xFF
        if key != 255:
            break

    cv2.destroyAllWindows()


def main_3():
    # load background (RGB) and sprite images
    bg_image = cv2.imread(r'c:\temp\lenna.png')

    # Initialize the sprites data
    sprites_data = load_sprites_3(bg_image, multiply=50)

    print(f"{len(sprites_data)} sprites loaded.")

    fps = FPSCounter(update_interval=0.5)
    render_buffer = np.zeros_like(bg_image, dtype=np.uint8)
    while True:
        if fps.update():
            print("  - current fps =", fps)

        np.copyto(render_buffer, bg_image)
        for sprite_data in sprites_data:
            # extract sprite data into variables for readability
            sp_x, sp_y, sp_dx, sp_dy = sprite_data['x'], sprite_data['y'], sprite_data['dx'], sprite_data['dy']
            sp_image, sp_alpha_inv = sprite_data['image'][:, :, :3], sprite_data['image'][:, :, 3]

            # make (x, y, dx, dy) change like a box bouncing around the screen
            if sp_x + sp_image.shape[1] + sp_dx > bg_image.shape[1] or sp_x + sp_dx < 0:
                sp_dx = -sp_dx
            if sp_y + sp_image.shape[0] + sp_dy > bg_image.shape[0] or sp_y + sp_dy < 0:
                sp_dy = -sp_dy

            # update sprite positions
            sp_x += sp_dx
            sp_y += sp_dy
            sprite_data['x'], sprite_data['y'] = sp_x, sp_y
            sprite_data['dx'], sprite_data['dy'] = sp_dx, sp_dy
            sp_height, sp_width, _ = sp_image.shape

            sp_x, sp_y = int(sp_x), int(sp_y)

            # blit fg_sprite to at x, y
            # roi = render_buffer[sp_y:sp_y + sp_image.shape[0], sp_x:sp_x + sp_image.shape[1]]
            # np.add(sp_image[:, :, :3], roi * sp_alpha_inv, out=roi, casting="unsafe")
            # blit fg_sprite to at x, y
            # roi = render_buffer[sp_y:sp_y + sp_image.shape[0], sp_x:sp_x + sp_image.shape[1]]
            # np.add(sp_image, roi * sp_alpha_inv[..., np.newaxis], out=roi, casting="unsafe")
            roi = render_buffer[sp_y:sp_y + sp_height, sp_x:sp_x + sp_width]
            np.add(sp_image, roi * sp_alpha_inv[..., np.newaxis], out=roi, casting="unsafe")

        # convert render_buffer to 8-bit image
        render_buffer = cv2.convertScaleAbs(render_buffer)

        # Display the image
        cv2.imshow(f'{len(sprites_data)} Sprites', render_buffer)

        # exit on any key
        key = cv2.waitKey(1) & 0xFF
        if key != 255:
            break

    cv2.destroyAllWindows()


if __name__ == '__main__':
    main_2()
