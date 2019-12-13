from time import time, sleep

from can import MessageSync


class MessageSync2(MessageSync):
    def __init__(self, messages, timestamps=True, gap=0.0001, skip=60, start=None):
        super().__init__(messages, timestamps, gap, skip)
        self.start = start

    def __iter__(self):
        playback_start_time = time()
        recorded_start_time = None

        for message in self.raw_messages:
            if self.start is not None and message.timestamp < self.start:
                ##print(self.start,'/',message.timestamp)
                continue
                
            # Work out the correct wait time
            if self.timestamps:
                if recorded_start_time is None:
                    recorded_start_time = message.timestamp

                now = time()
                current_offset = now - playback_start_time
                recorded_offset_from_start = message.timestamp - recorded_start_time
                remaining_gap = max(0.0, recorded_offset_from_start - current_offset)

                sleep_period = max(self.gap, min(self.skip, remaining_gap))
            else:
                sleep_period = self.gap

            sleep(sleep_period)

            yield message
