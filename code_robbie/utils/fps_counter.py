import time

class FPSCounter:
    """
    A FPS counter.

    eg:
        while True:
            if fps.update():
                print(f"Current fps (over the last second) = {fps}")  # fps prints as a float

               if fps < 30:
                    logging.warning(low_fps)
    """
    def __init__(self, update_interval: float = 1, decimal_places: int = 1):
        self.update_interval = update_interval
        self.decimal_places = decimal_places
        self.start_time = None
        self.frame_count = 0
        self._fps_raw = 0.0
        self.estimated_next_update_frame = 100
        self.fps_rounded = 0

    def update(self):
        """
        Updates the frame count, and if the estimated frame count for the update interval has been reached,
        calculates the FPS and resets the frame count and start time.
        """
        if self.start_time is None:
            self.start_time = time.time()
            self.frame_count = 0
            return False

        self.frame_count += 1

        if self.frame_count >= self.estimated_next_update_frame:
            now = time.time()
            elapsed_time = now - self.start_time
            self._fps_raw = self.frame_count / elapsed_time
            self.fps_rounded = round(self._fps_raw, self.decimal_places)
            self.start_time = now
            self.frame_count = 0
            self.estimated_next_update_frame = self.frame_count + max(1, int(self._fps_raw * self.update_interval))
            return True

        return False

    def __str__(self):
        return f"{self._fps_raw:.{self.decimal_places}f}"

    def __float__(self):
        return self.fps_rounded
