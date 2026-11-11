from concurrent.futures import ThreadPoolExecutor

import pytest

from surgical_perception_runtime.core import validate_device
from surgical_perception_runtime.latest_frame import LatestFrame


def test_latest_frame_replaces_pending_image(real_image):
    buffer = LatestFrame()
    old_frame = real_image.copy()
    newest_frame = real_image.copy()
    buffer.put(old_frame)
    buffer.put(newest_frame)
    assert buffer.take() is newest_frame
    buffer.close()
    assert buffer.take() is None


def test_close_wakes_waiting_worker():
    buffer = LatestFrame()
    with ThreadPoolExecutor(max_workers=1) as executor:
        waiting = executor.submit(buffer.take)
        buffer.close()
        assert waiting.result(timeout=2) is None


def test_invalid_device_fails():
    with pytest.raises(ValueError, match="device"):
        validate_device("unavailable-device")
