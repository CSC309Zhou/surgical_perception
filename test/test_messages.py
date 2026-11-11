import numpy as np
import pytest
from cv_bridge import CvBridge
from rclpy.serialization import deserialize_message, serialize_message
from sensor_msgs.msg import Image
from std_msgs.msg import Header
from surgical_perception.msg import InstrumentArray

from surgical_perception_runtime.core import Segmenter, resolve_weights
from surgical_perception_runtime.messages import to_message


@pytest.mark.parametrize("size", ["s", "m", "l"])
def test_real_prediction_round_trip(real_image, package_share, size):
    bridge = CvBridge()
    image_msg = bridge.cv2_to_imgmsg(real_image, encoding="bgr8")
    image_msg.header = Header(frame_id="endoscope_optical_frame")
    image_msg.header.stamp.sec = 123
    image_msg.header.stamp.nanosec = 456
    decoded = bridge.imgmsg_to_cv2(
        deserialize_message(serialize_message(image_msg), Image), "bgr8")
    np.testing.assert_array_equal(decoded, real_image)
    model = Segmenter(resolve_weights(package_share, size))
    prediction = model.predict(decoded, overlay=True)
    assert prediction.instances, "测试图像需要包含能被模型检测到的器械"
    message = to_message(prediction, image_msg.header, bridge)
    restored = deserialize_message(serialize_message(message), InstrumentArray)
    assert restored.header == image_msg.header
    assert (restored.image_height, restored.image_width) == real_image.shape[:2]
    for index, (before, after) in enumerate(zip(prediction.instances, restored.instances)):
        assert after.instance_id == index
        assert after.class_id == before.class_id
        assert after.class_name == before.class_name
        assert after.confidence == pytest.approx(before.confidence)
        np.testing.assert_allclose(after.bbox_xyxy, before.bbox_xyxy)
        assert after.mask.header == image_msg.header
        assert after.mask.encoding == "mono8"
        np.testing.assert_array_equal(bridge.imgmsg_to_cv2(after.mask), before.mask)
    assert len(restored.instances) == len(prediction.instances)
    # 对真实图像使用最高阈值，验证实际模型的空检测输出。
    model.confidence = 1.0
    empty = model.predict(real_image)
    assert not empty.instances
    empty_msg = to_message(empty, image_msg.header, bridge)
    assert not deserialize_message(serialize_message(empty_msg), InstrumentArray).instances
