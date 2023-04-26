import sys
import time

class DotBar:
    def __init__(self, iterable, total=None, bar_len=20, heading="loading"):
        self.iterable = iterable
        self.total = total or len(iterable)
        self.bar_len = bar_len
        self.braille_chars = ["⠁", "⠃", "⠇", "⡇", "⡏", "⡟", "⡿", "⣿"]
        self.blank_braille_char = '\u2800'
        self.heading = heading

    def __iter__(self):
        # for index, item in enumerate(self.iterable):
        #     self.update(index + 1)
        #     yield item
        # self.update(self.total)
        # print()
        index = 0
        try:
            for index, item in enumerate(self.iterable):
                self.update(index + 1)
                yield item
        finally:
            self.update(index, early_finish=True)
            print()

    def update(self, progress, early_finish=False):
        if not early_finish:
            complete_bars = int(progress * self.bar_len / self.total)
            last_bar_progress = int((progress * self.bar_len * 8) / self.total) % 8
            bars = [self.braille_chars[-1]] * complete_bars
            if complete_bars < self.bar_len:
                bars.append(self.braille_chars[last_bar_progress])
                bars.extend([self.blank_braille_char] * (self.bar_len - complete_bars - 1))
            progress_bar = ''.join(bars)
            sys.stdout.write(f"\r{self.heading}: [{progress_bar}] {progress}/{self.total}")
        else:
            progress_bar = "⣿" * self.bar_len
            sys.stdout.write(f"\r{self.heading}: [{progress_bar}] finished after {progress}")
        sys.stdout.flush()

# Usage example
if __name__ == "__main__":
    items = list(range(100))
    for item in DotBar(items, heading="  - wait for tts system start", bar_len=5):
        time.sleep(0.05)
        if item == 21:
            break
