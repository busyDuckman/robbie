import numpy as np
from PIL import Image


class EyeRenderer:
    def __init__(self, w, h,
                 eye_color = (255, 255, 255),
                 pupil_color = (0, 100, 255),
                 iris_color = (0, 0, 0)):
        self.w = w
        self.h = h

        self.eye_radius = min(w, h) // 2
        self.pupil_radius = self.eye_radius // 4
        self.iris_radius = self.eye_radius // 2

        self.iris_color = iris_color
        self.pupil_color = pupil_color
        self.eye_color = eye_color

        img = self._render_eye_pil()
        self.img_eye_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)

        img = self._render_pupil_pil()
        self.img_pupil_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)

        img = self._render_iris_pil()
        self.img_iris_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGRA)
        # TODO more

    def _render_iris_pil(self) -> Image.Image:
        pass

    def _render_pupil_pil(self) -> Image.Image:
        pass

    def _render_eye_pil(self) -> Image.Image:
        pass

    def compose_eye(pd, point_to_look_at, dest_buffer) -> None:
        pass

