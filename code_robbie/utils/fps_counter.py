import time

from utils.sleep_manager import SleepManager


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
        self.last_frame_time = time.time()

        # fps that would be possible if frame limiting was not in place.
        self.unlimited_fps = 0.0
        self.sleep_time = 0.0

    def update(self, limit_fps=0, now=None):
        """
        Updates the frame count, and if the estimated frame count for the update interval has been reached,
        calculates the FPS and resets the frame count and start time.
        :param limit_fps: If > 0, causes a sleep statement to dynamically delay any frame
                          rendering faster than the limit.
        :param now: Do you have and existing time.time() for the current frame?
        """
        if self.start_time is None:
            self.start_time = time.time()
            self.frame_count = 0
            return False

        self.frame_count += 1

        if limit_fps > 0:
            now = time.time() if now is None else now

            if self.frame_count > 0:
                elapsed_time = now - self.start_time
                elapsed_time = max(elapsed_time, 0.000001)  # stop div 0 in the event of a low res timer.
                fps_raw = self.frame_count / elapsed_time
                if fps_raw > (limit_fps + 0.25):
                    target_frame_time = 1.0 / limit_fps
                    time.sleep(target_frame_time/2)
                    sleep_end = time.time()
                    actual_sleep_time = sleep_end - now
                    self.sleep_time += actual_sleep_time
                    self.last_frame_time = sleep_end
                else:
                    self.last_frame_time = now

            # target_frame_time = 1.0 / limit_fps
            # elapsed_frame_time = now - self.last_frame_time
            # remaining_frame_time = target_frame_time - elapsed_frame_time
            # if remaining_frame_time > 0:
            #     actual_sleep_time = self.sleep_manager.sleep(remaining_frame_time)
            #     end_sleep = time.time()
            #     self.sleep_time += actual_sleep_time
            #     self.last_frame_time = end_sleep
            # else:
            #     self.last_frame_time = now

        if self.frame_count >= self.estimated_next_update_frame:
            now = time.time() if now is None else now
            elapsed_time = now - self.start_time
            self._fps_raw = self.frame_count / elapsed_time
            self.fps_rounded = round(self._fps_raw, self.decimal_places)
            self.start_time = now
            self.frame_count = 0
            self.estimated_next_update_frame = self.frame_count + max(1, int(self._fps_raw * self.update_interval))

            # calculate the unlimited_fps in the event of frame rate limiting
            if self.sleep_time > 0:
                self.unlimited_fps = round(self._fps_raw * (1 + self.sleep_time / max(elapsed_time, 0.00000001)), self.decimal_places)
            else:
                self.unlimited_fps = self.fps_rounded
            self.sleep_time = 0.0
            return True

        return False

    def __str__(self):
        return f"{self._fps_raw:.{self.decimal_places}f}"

    def __float__(self):
        return self.fps_rounded

    def summary(self):
        if self.unlimited_fps != self.fps_rounded:
            return f"{self.fps_rounded} fps (limited), {self.unlimited_fps} if unlimited."
        else:
            return f"{self.fps_rounded} fps"
