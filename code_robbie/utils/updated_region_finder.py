from enum import Enum

import cv2
import numpy as np
from PIL import ImageChops
from scipy.ndimage import label

from numba import njit, jit


@jit(nopython=True)
def any_along_last_axis(arr):
    result = np.zeros_like(arr[..., 0], dtype=np.bool_)
    for i in range(arr.shape[-1]):
        result |= arr[..., i]
    return result



def regions_by_separate_region(image1, image2):
    min_area = 1
    # Calculate the difference between the two images
    # diff = ImageChops.difference(image1, image2)
    diff = cv2.absdiff(image1, image2)

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

@njit
def grow_rec_old(diff, x, y, threshold=16):
    """
    creates a 1 x 1 rec at x, y, using boolean values in diff.

    Iteratively attempt to increase the rec's width, then the recs height;
    until neither can be expanded further.

    The expansion condition is that all the following are met:
       - there is at least 1 true value in the new row/col added
       - there are no more than threshold false values in the new row/col added
       - the box does not outgrow the bounds of diff

    return (x1, x2, y1, y2)
    """
    height, width = diff.shape
    x1, y1, x2, y2 = x, y, x + 1, y + 1

    bingo = True

    while bingo:
        bingo = False
        while x2 < width:
            new_col = diff[y1:y2, x2:x2 + 1]
            new_col_sum = np.count_nonzero(new_col)
            if new_col_sum and (new_col.size - new_col_sum) <= threshold:
                x2 += 1
                bingo = True
            else:
                break

        while y2 < height:
            new_row = diff[y2:y2 + 1, x1:x2]
            new_row_sum = np.count_nonzero(new_row)
            if new_row_sum and (new_row.size - new_row_sum) <= threshold:
                y2 += 1
                bingo = True
            else:
                break

        while x1 > 0:
            new_col = diff[y1:y2, x1 - 1:x1]
            new_col_sum = np.count_nonzero(new_col)
            if new_col_sum and (new_col.size - new_col_sum) <= threshold:
                x1 -= 1
                bingo = True
            else:
                break

    return x1, y1, x2, y2


@njit
def grow_rec(diff, x, y, threshold=16):
    height, width = diff.shape
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




    # height, width = diff.shape
    # x1, y1, x2, y2 = x, y, x + 1, y + 1
    #
    # while x2 < width and np.count_nonzero(diff[y1:y2, x2:x2 + 1]) and np.count_nonzero(
    #         ~diff[y1:y2, x2:x2 + 1]) <= threshold:
    #     x2 += 1
    #
    # while y2 < height and np.count_nonzero(diff[y2:y2 + 1, x1:x2]) and np.count_nonzero(
    #         ~diff[y2:y2 + 1, x1:x2]) <= threshold:
    #     y2 += 1
    #
    # while x1 > 0 and np.count_nonzero(diff[y1:y2, x1-1:x1]) and np.count_nonzero(~diff[y1:y2, x1-1:x1]) <= threshold:
    #     x1 -= 1
    #
    # return x1, y1, x2, y2

@njit
def regions_by_fitted_rec(image1, image2):
    diff = np.abs(image1 - image2)
    # diff = np.any(diff > 0, axis=-1)
    diff = any_along_last_axis(diff > 0)
    num_pixels_changed = np.sum(diff)
    num_pixels_flagged = 0

    recs = []
    for y, x in np.ndindex(diff.shape):
        if diff[y, x]:
            rec = grow_rec(diff, x, y)
            x1, y1, x2, y2 = rec
            diff[y1:y2, x1:x2] = False
            recs.append(rec)

            w, h = x2-x1, y2-y1
            num_pixels_flagged += w * h

    return recs, num_pixels_changed, num_pixels_flagged


class RegionAlg(Enum):
    SEPARATE_REGION = regions_by_separate_region
    # SCAN_LINES = find_updated_regions_scan_lines
    FITTED_RECS = regions_by_fitted_rec

    def __call__(self, image1, image2):
        return self.value(image1, image2)