from threading import Condition


class LatestFrame:
    def __init__(self):
        self._condition = Condition()
        self._frame = None
        self._closed = False

    def put(self, frame):
        with self._condition:
            if not self._closed:
                self._frame = frame
                self._condition.notify()

    def take(self):
        with self._condition:
            self._condition.wait_for(lambda: self._closed or self._frame is not None)
            if self._closed:
                return None
            frame, self._frame = self._frame, None
            return frame

    def close(self):
        with self._condition:
            self._closed = True
            self._frame = None
            self._condition.notify_all()
