from concurrent.futures import ThreadPoolExecutor
import signal
from threading import Event

from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge
import rclpy
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import Image
from surgical_perception.msg import InstrumentArray

from .core import Segmenter, resolve_weights
from .latest_frame import LatestFrame
from .messages import to_message


class PerceptionNode(Node):
    def __init__(self):
        super().__init__("surgical_perception")
        defaults = dict(image_topic="/endoscope/image_raw", model_size="s", device="cpu",
                        imgsz=640, confidence=0.25, publish_overlay=True)
        for name, value in defaults.items():
            self.declare_parameter(name, value, ParameterDescriptor(read_only=True))
        values = {name: self.get_parameter(name).value for name in defaults}
        weights = resolve_weights(get_package_share_directory("surgical_perception"),
                                  values["model_size"])
        self.segmenter = Segmenter(weights, values["device"], values["imgsz"], values["confidence"])
        self.bridge = CvBridge()
        self.frames = LatestFrame()
        self.publish_overlay = values["publish_overlay"]
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST)
        self.instances = self.create_publisher(InstrumentArray, "~/instances", qos)
        self.overlay = self.create_publisher(Image, "~/overlay", qos)
        self.subscription = self.create_subscription(Image, values["image_topic"], self.frames.put, qos)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="perception")
        self.worker = self.pool.submit(self._run)
        self.health_timer = self.create_timer(0.1, self._check_worker)
        self.get_logger().info(f"已加载 YOLO26{values['model_size']}-seg，设备 {self.segmenter.device}")

    def _check_worker(self):
        if self.worker.done():
            # Future 将推理异常传回执行器，保留原始错误及调用位置。
            self.worker.result()

    def _run(self):
        while rclpy.ok(context=self.context):
            frame = self.frames.take()
            if frame is None:
                return
            image = self.bridge.imgmsg_to_cv2(frame, desired_encoding="bgr8")
            draw = self.publish_overlay and self.overlay.get_subscription_count() > 0
            prediction = self.segmenter.predict(image, overlay=draw)
            if not rclpy.ok(context=self.context):
                return
            self.instances.publish(to_message(prediction, frame.header, self.bridge))
            if draw:
                annotated = self.bridge.cv2_to_imgmsg(prediction.overlay, encoding="bgr8")
                annotated.header = frame.header
                self.overlay.publish(annotated)

    def destroy_node(self):
        self.frames.close()
        self.pool.shutdown(wait=True)
        try:
            self.worker.result()
        finally:
            super().destroy_node()


def main():
    # 先等待推理线程退出，再关闭 ROS context，避免发布期间销毁通信资源。
    stop = Event()
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    previous = {sig: signal.signal(sig, lambda *_: stop.set())
                for sig in (signal.SIGINT, signal.SIGTERM)}
    node = None
    try:
        node = PerceptionNode()
        while rclpy.ok() and not stop.is_set():
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        try:
            if node is not None:
                node.destroy_node()
        finally:
            if rclpy.ok():
                rclpy.shutdown()
            for sig, handler in previous.items():
                signal.signal(sig, handler)


if __name__ == "__main__":
    main()
