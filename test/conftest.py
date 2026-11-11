import os
from pathlib import Path

import cv2
import pytest


@pytest.fixture(scope="session")
def real_image():
    path = Path(os.environ["SURGICAL_TEST_IMAGE"])
    image = cv2.imread(str(path))
    assert image is not None, f"无法读取真实测试图像：{path}"
    return image


@pytest.fixture(scope="session")
def package_share():
    from ament_index_python.packages import get_package_share_directory
    return Path(get_package_share_directory("surgical_perception"))
