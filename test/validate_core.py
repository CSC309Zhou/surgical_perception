import argparse
import json
import platform
from importlib.metadata import version
from pathlib import Path

import cv2
import numpy as np
import torch

from surgical_perception_runtime.core import CLASS_NAMES, Segmenter, resolve_weights


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resize", type=int, nargs=2, metavar=("WIDTH", "HEIGHT"))
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    image = cv2.imread(str(args.image))
    if image is None:
        raise ValueError(f"无法读取真实图像：{args.image}")
    if args.resize:
        image = cv2.resize(image, tuple(args.resize))
    torch.set_num_threads(4)
    report = {"python": platform.python_version(), "platform": platform.platform(),
              "device": args.device,
              "versions": {name: version(name) for name in
                           ("torch", "torchvision", "ultralytics", "numpy", "opencv-python")},
              "image": str(args.image), "resize": args.resize,
              "shape": list(image.shape), "models": {}}
    for size in ("s", "m", "l"):
        model = Segmenter(resolve_weights(args.package, size), device=args.device)
        prediction = model.predict(image, overlay=True)
        assert prediction.overlay.shape == image.shape
        assert prediction.overlay.dtype == np.uint8
        assert prediction.instances, "真实样例上未检测到器械"
        for item in prediction.instances:
            assert item.class_name == CLASS_NAMES[item.class_id]
            assert 0.25 <= item.confidence <= 1
            x1, y1, x2, y2 = item.bbox_xyxy
            assert 0 <= x1 <= x2 <= prediction.width
            assert 0 <= y1 <= y2 <= prediction.height
            assert item.mask.shape == image.shape[:2]
            assert item.mask.dtype == np.uint8
            assert set(np.unique(item.mask)).issubset({0, 255})
            assert item.mask.any()
        model.confidence = 1.0
        empty = model.predict(image)
        assert empty.instances == [] and empty.overlay is None
        report["models"][size] = {
            "instances": len(prediction.instances),
            "classes": [item.class_name for item in prediction.instances],
            "weights_bytes": resolve_weights(args.package, size).stat().st_size,
            "checks": "类别、检测框、原图掩膜、叠加图、空检测输出通过",
        }
        print(size, report["models"][size], flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
