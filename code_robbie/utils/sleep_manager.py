import time


class SleepManager:
    """
    time.sleep(...) may overshoot the mark, making using it for timing difficult.
    This class keeps a tally of accumulated error and adjusts sleep calls to suit.
    """
    def __init__(self, duration_hint):
        """
        Creates a new SleepManager.
        :param duration_hint: The expected sleep duration.
                              Estimate higher if unsure.
        """
        self.error = 0.0
        self.last_frame_time = time.time()

        # What we can expect the shortest possible sleep to return
        self.min_sleep = 0.0

        # the mean error, for sleeps longer than the minimum.
        self.mean_error = 0.0

        start_time = time.time()
        for _ in range(100):
            # very small sleep; should overshoot
            time.sleep(1.0/100_000)
        duration = time.time() - start_time
        self.min_sleep = duration / 100

        sleep = max(duration_hint, self.min_sleep * 4)
        n = 100
        if sleep > 0.2:
            sleep = 0.2
            n = 50
        start_time = time.time()
        for _ in range(n):
            # normal sleep
            time.sleep(sleep)
        duration = time.time() - start_time
        self.mean_error = (duration / n) - sleep

        # Percent extra wait that is permissible if running ahead of time.
        self.max_overtime_ratio = 2
        self.max_abs_error = duration_hint * 10

    def reset(self):
        self.error = 0.0

    def sleep(self, duration, now=None):
        now = time.time() if now is None else now

        if self.error > duration:
            # we are running way behind, no time to sleep
            self.error -= duration
            return 0
        elif self.error >= 0:
            # we are running marginally behind
            # adjust sleep to correct for error
            desired_duration = duration - self.error
            estimated_duration = desired_duration - self.mean_error
            if estimated_duration < (self.min_sleep / 2):
                # doing a sleep would make things worse, not better
                self.error -= duration
                return 0
        elif self.error < 0:
            # we are running ahead of time, not enough delay
            desired_duration = duration - self.error
            estimated_duration = desired_duration - self.mean_error
            estimated_duration = min(estimated_duration, duration * self.max_overtime_ratio)

        # do the sleep
        if estimated_duration < 0:
            self.error -= duration
            return 0

        start_sleep = now
        time.sleep(estimated_duration)
        actual_duration = time.time() - start_sleep
        error = actual_duration - duration
        self.error += error
        self.error = max(-self.max_abs_error, self.error)
        self.error = min(self.max_abs_error, self.error)

        return actual_duration
