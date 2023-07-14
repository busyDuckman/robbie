"""
A numba specific atrocity to store a dynamic list of regions.
"""

import numpy as np
from numba import njit, jit

@njit
def diff(img1, img2, x, y):
    return img1[x, y] != img2[x, y]

@njit
def grow_rec(img1, img2, x, y, threshold=16):
    height, width = img1.shape
    x1, y1, x2, y2 = x, y, x + 3, y + 3

    slope = 2

    growing = True
    while growing:
        growing = False

        if x2 < (width-1) and (diff[y1+slope, x2+1] or diff[y2-slope, x2+1]):
            # step = max(x2 - x1 / 4, 1)
            x2 += 1
            growing = True

        if x1 > 0 and (diff[y1+slope, x1-1] or diff[y2-slope, x1-1]):
            x1 -= 1
            growing = True

        if y2 < (height-1) and (diff[y2+1, x1+slope] or diff[y2+1, x2-slope]):
            y2 += 1
            growing = True

    return x1, y1, x2, y2

@njit
def regions_by_fitted_rec_uint32(image1, image2, recs):
    h, w = image1.shape
    recs = []
    for y in range(h):
        for x in range(w):
            if image1[y, x] != image2[y, x]:
                rec = grow_rec(image1, image2, x, y)

    # return recs, num_recs, num_pixels_changed, num_pixels_flagged
    return recs, 0, 0, 0
















@njit
def remove_element(storage, index):
    pos, lengths, dirty, count = storage
    dirty[index] = 1
    count -= 1
    return pos, lengths, dirty, count

@njit
def add_element(storage, pos, length):
    positions, lengths, dirty, count = storage
    positions.append(pos)
    lengths.append(length)
    dirty.append(0)
    count += 1
    return positions, lengths, dirty, count

@njit
def create_dirty_list(max_size):
    positions = np.zeros(max_size, dtype=np.int16)
    lengths = np.zeros(max_size, dtype=np.int16)
    dirty = np.zeros(max_size, dtype=np.uint8)
    count = 0
    return positions, lengths, dirty, count

# @njit
# def iterate_list(storage):
#     positions, lengths, dirty, count = storage
#     pos = 0
#     for index in range(len(positions)):
#         if dirty[index] == 0:
#             yield positions[index], lengths[index]
#             pos += 1
#             if pos >= count:
#                 break

# @njit
# def regions_by_fitted_rec_uint32(image1, image2):
#     h, w = image1.shape
#     dirty_lut = [create_dirty_list(w) for _ in h]
#
#     # find all runs
#     for y in range(h):
#         run = 0
#         for x in range(w):
#             dirty = image1[y, x] != image2[y, x]
#             if dirty:
#                 run += 1
#             elif run > 0:
#                 add_element(dirty_lut[y], x-run, run)
#                 run = 0
#         if run > 0:
#             add_element(dirty_lut[y], x - run, run)
#
#     slope = 2
#
#     boxes = []
#     current_box = None
#     for y in range(h):
#         # we look ror the start of the next box
#
#         positions, lengths, deleted, count = dirty_lut[y]
#         if count == 0:
#             continue
#
#         actual_index = 0
#         for index in range(len(positions)):
#             if not deleted[index]:
#                 # we start a new box and find it's size
#                 # removing runs as it consumes them
#                 pos, length = positions[index], lengths[index]
#                 x1, x2 = pos, pos+length
#                 y1, y2 = y, y
#
#                 count = grow_box(x1, x2, y1, y2, )
#
#                 # check for early end
#                 actual_index += 1
#                 if actual_index >= (count-1):
#                     break
#
#         current_box :
#             current_box = ()



