from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO


CLASS_NAMES = ("grasper", "hook", "irrigator", "clipper", "bipolar", "scissors", "snare")


@dataclass(frozen=True)
class Instance:
    class_id: int
    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]
    mask: np.ndarray


@dataclass(frozen=True)
class Prediction:
    width: int
    height: int
    instances: list[Instance]
    overlay: np.ndarray | None


def resolve_weights(share_directory, model_size):
    if model_size not in ("s", "m", "l"):
        raise ValueError("model_size 必须为 s、m 或 l")
    path = Path(share_directory) / "weights" / model_size / "best.pt"
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("rb") as stream:
        if stream.read(80).startswith(b"version https://git-lfs.github.com/spec/v1"):
            raise ValueError(f"权重仍为 Git LFS 指针，请执行 git lfs pull：{path}")
    return path


def validate_device(device):
    if device == "cpu":
        return device
    index = device.removeprefix("cuda:")
    if not index.isdigit():
        raise ValueError("device 必须为 cpu、CUDA 编号或 cuda:编号")
    if not torch.cuda.is_available() or int(index) >= torch.cuda.device_count():
        raise ValueError(f"指定的 CUDA 设备不可用：{device}")
    return f"cuda:{int(index)}"


class Segmenter:
    def __init__(self, weights, device="cpu", imgsz=640, confidence=0.25):
        if not isinstance(imgsz, int) or imgsz <= 0 or imgsz % 32:
            raise ValueError("imgsz 必须为正整数且是 32 的倍数")
        if not np.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("confidence 必须在 0 到 1 之间")
        self.device = validate_device(device)
        self.imgsz = imgsz
        self.confidence = confidence
        self.model = YOLO(str(weights), task="segment")
        if self.model.task != "segment":
            raise ValueError("权重必须是实例分割模型")
        if self.model.names != dict(enumerate(CLASS_NAMES)):
            raise ValueError(f"权重类别与预期不符：{self.model.names}")
        self.model.to(self.device)

    def predict(self, image, overlay=False):
        if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("输入必须是 uint8 HWC 三通道 BGR 图像")
        height, width = image.shape[:2]
        if height == 0 or width == 0:
            raise ValueError("输入图像不能为空")
        result = self.model.predict(
            source=image, device=self.device, imgsz=self.imgsz,
            conf=self.confidence, retina_masks=True, batch=1,
            quantize=32, verbose=False, save=False,
        )[0]
        instances = []
        if len(result.boxes):
            if result.masks is None or len(result.masks) != len(result.boxes):
                raise RuntimeError("检测框与实例掩膜数量不一致")
            masks = result.masks.data.cpu().numpy()
            if masks.shape[1:] != (height, width):
                raise RuntimeError("掩膜尺寸与原图不一致")
            boxes = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()
            for box, score, class_id, mask in zip(boxes, scores, classes, masks):
                class_id = int(class_id)
                instances.append(Instance(
                    class_id, CLASS_NAMES[class_id], float(score),
                    tuple(float(value) for value in box),
                    np.ascontiguousarray(mask > 0.5, dtype=np.uint8) * 255,
                ))
        return Prediction(width, height, instances, result.plot() if overlay else None)
