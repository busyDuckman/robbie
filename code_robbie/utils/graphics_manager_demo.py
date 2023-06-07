import cv2
import numpy as np

from utils.graphics_manager import Composer, Sprite, rescale_img, generate_debug_image
from utils.fps_counter import FPSCounter
from utils.interlaced_graphics_manager import InterlacedComposer
from utils.updated_region_finder import RegionAlg


def _demo_load_sprites(g: Composer, multiply=1):
    import glob
    import random

    random.seed(1337)
    sprites_data = []
    w, h = g.width, g.height

    for q, filename in enumerate(glob.glob(r'C:\temp\dbx_sprite_*.png')):
        sprite_image = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        sprite_image = rescale_img(sprite_image, 0.3)
        sprite = g.get_native_sprite(sprite_image)

        for z in range(multiply):

            sprite_data = {
                'sprite': sprite,
                'x': (128 + random.randint(0, 512)) % (w - sprite_image.shape[1] - 1),
                'y': (256 + random.randint(0, 512)) % (h - sprite_image.shape[0] - 1),
                'dx': random.random() * 4 - 2,
                'dy': random.random() * 4 - 2,
            }
            # print(sprite_data)
            sprites_data.append(sprite_data)
    random.shuffle(sprites_data)
    return sprites_data


def _demo():
    # load background (RGB) and sprite images
    bg_image = cv2.imread(r'c:\temp\lenna.png')
    w = bg_image.shape[1]
    h = bg_image.shape[0]

    # create a graphics manager
    interlaced = False
    if interlaced:
        g = InterlacedComposer(w, h)
        screen_buffer = np.zeros((w, h, 3), dtype=np.uint8)
    else:
        g = Composer(w, h)

    print("Composer: ", g)

    # Initialize the sprites data
    sprites_data = _demo_load_sprites(g, multiply=1)

    # sprites_data = [{
    #     'sprite': g.get_native_sprite("c:\\temp\\cir.png"),
    #     'x': 10,
    #     'y': 10,
    #     'dx': 1,
    #     'dy': 1,
    # }]

    print(f"{len(sprites_data)} sprites loaded.")

    # Window needs to be a set size, or resizing effects obscure algorithmic results..
    # cv2.namedWindow('demo', cv2.WINDOW_NORMAL)
    cv2.namedWindow('demo', cv2.WINDOW_AUTOSIZE)
    cv2.resizeWindow('demo', w*2, h)

    fps = FPSCounter(update_interval=1)
    frame = 0
    boxes = []
    n_flagged = n_changed = 0

    while True:
        if fps.update(limit_fps=60):
            print("  - " + fps.summary())
            print("  - num boxes =", len(boxes))
            bytes_sent = (len(boxes) * 6) + (n_flagged * 3)
            waste = n_flagged - n_changed
            print(f"  - waste  = {waste:,} pixels, {100.0 * waste/(w*h):.2f}% of image")
            print(f"  - change = {n_changed:,} pixels, {100.0 * n_changed / (w * h):.2f}% of image")
            print(f"  - bytes sent  = {bytes_sent:,}")
            print(f"  - bytes saved = {(w*h*3)-bytes_sent:,}")
            print()



        # np.copyto(g.draw_buffer, bg_image)
        g.clear_screen()

        for sprite_data in sprites_data:
            # extract sprite data into variables for readability
            sp_x, sp_y, sp_dx, sp_dy = [sprite_data[q] for q in ['x', 'y', 'dx', 'dy']]
            sprite = sprite_data['sprite']

            # make (x, y, dx, dy) change like a box bouncing around the screen
            if sp_x + sprite.width + sp_dx > g.width or sp_x + sp_dx < 0:
                sp_dx = -sp_dx
            if sp_y + sprite.height + sp_dy > g.height or sp_y + sp_dy < 0:
                sp_dy = -sp_dy

            # update sprite positions
            sp_x += sp_dx
            sp_y += sp_dy
            sprite_data['x'], sprite_data['y'] = sp_x, sp_y
            sprite_data['dx'], sprite_data['dy'] = sp_dx, sp_dy
            sp_x, sp_y = int(sp_x), int(sp_y)

            # blit fg_sprite to at x, y
            g.draw_sprite(sprite, sp_x, sp_y)

        # convert render_buffer to 8-bit image
        # render_buffer = cv2.convertScaleAbs(g.draw_buffer)
        if not interlaced:
            render_buffer = g.draw_buffer
        else:
            g.render_test_rows(screen_buffer)
            render_buffer = screen_buffer


        # Display the image
        boxes, n_changed, n_flagged = g.find_dirty_recs(RegionAlg.FITTED_RECS)

        # boxes = g.find_dirty_recs(RegionAlg.SEPARATE_REGION)
        dbg_image = generate_debug_image(render_buffer, boxes)
        dbg_image[:, 0] = [128, 128, 128]  # gray line to separate images on screen.

        img = np.concatenate((render_buffer, dbg_image), axis=1)
        # cv2.imshow(f'{len(sprites_data)} Sprites', img)
        # cv2.resizeWindow('demo', 1024, 512)
        cv2.imshow('demo', img)
        # if frame == 0:


        # exit on any key
        frame += 1
        g.next_frame()

        key = cv2.waitKey(1) & 0xFF
        if key != 255:
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    _demo()
