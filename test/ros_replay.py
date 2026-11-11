import argparse
import time
from pathlib import Path

import cv2
from cv_bridge import CvBridge
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from surgical_perception.msg import InstrumentArray


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--expect-empty", action="store_true")
    args = parser.parse_args()
    image = cv2.imread(str(args.image))
    if image is None:
        raise ValueError(f"无法读取真实图像：{args.image}")
    rclpy.init()
    node = Node("surgical_perception_replay_check")
    bridge = CvBridge()
    received, overlays, sent = [], [], set()
    publisher = node.create_publisher(Image, "/endoscope/image_raw", qos_profile_sensor_data)
    node.create_subscription(InstrumentArray, "/surgical_perception/instances",
                             received.append, qos_profile_sensor_data)
    node.create_subscription(Image, "/surgical_perception/overlay",
                             overlays.append, qos_profile_sensor_data)
    deadline = time.monotonic() + args.timeout
    next_send = 0.0
    try:
        while time.monotonic() < deadline and (not received or not overlays):
            if time.monotonic() >= next_send:
                message = bridge.cv2_to_imgmsg(image, encoding="bgr8")
                message.header.frame_id = "endoscope_optical_frame"
                message.header.stamp = node.get_clock().now().to_msg()
                sent.add((message.header.stamp.sec, message.header.stamp.nanosec))
                publisher.publish(message)
                next_send = time.monotonic() + 0.05
            rclpy.spin_once(node, timeout_sec=0.01)
        assert received and overlays, "未在限时内收到感知结果和叠加图"
        for output in [*received, *overlays]:
            assert output.header.frame_id == "endoscope_optical_frame"
            assert (output.header.stamp.sec, output.header.stamp.nanosec) in sent
        result = received[-1]
        assert (result.image_height, result.image_width) == image.shape[:2]
        if args.expect_empty:
            assert not result.instances
        else:
            assert result.instances
        for instance in result.instances:
            mask = bridge.imgmsg_to_cv2(instance.mask, "mono8")
            assert mask.shape == image.shape[:2]
            assert set(np.unique(mask)).issubset({0, 255})
            assert instance.mask.header == result.header
        assert bridge.imgmsg_to_cv2(overlays[-1], "bgr8").shape == image.shape
        print(f"真实图像 ROS 回放通过，收到 {len(received)} 帧感知结果")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
