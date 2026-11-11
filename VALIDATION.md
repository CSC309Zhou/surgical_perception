# 验证记录

验证日期：2026-11-11。

## Mac 本地验证

| 检查 | 环境与结果 |
|---|---|
| s、m、l 真实权重加载和推理 | macOS ARM、Python 3.10.20，全部通过 |
| 854×480 真实验证图像 | 三个模型各检测到一个 grasper，检测框、类别和原图掩膜检查通过 |
| 1920×1080 图像输入 | 将另一张真实数据集图像缩放到该尺寸；三个模型各检测到两个 grasper，逐实例掩膜尺寸和二值编码检查通过 |
| 空检测输出 | 真实图像使用置信度阈值 1.0，三个模型均返回空列表；未使用伪造预测结果 |
| 叠加图 | 三个模型的输出尺寸与输入一致，类型为 uint8；未启用时返回 None |
| 最新帧缓存、关闭唤醒、非法设备参数 | `test_runtime.py` 的三个测试通过 |
| Python 语法与 shell 语法 | Python 3.10 编译检查、`bash -n` 通过 |

真实推理环境版本：

| 依赖 | 版本 |
|---|---|
| Python | 3.10.20 |
| Ultralytics | 8.4.190 |
| PyTorch | 2.14.1 |
| torchvision | 0.29.1 |
| NumPy | 1.26.4 |
| opencv-python | 4.11.0.86 |

机器可读结果保存在 `validation/core-macos-py310.json`、`validation/core-macos-py310-1080p.json` 与 `validation/runtime.xml`。这些是工程正确性检查，不是新的模型精度评估或实时性能测量。

## Ubuntu / ROS 2 Humble 验证

实际测试电脑：Ubuntu 22.04.5 LTS，32 GB 内存，RTX 4060 Laptop GPU（8 GB），NVIDIA 驱动 595.99.02。

工作空间：`/home/user/yolofinetune/surgical_perception_ws`。软件包已实际编译、安装并运行，测试进程结束后已全部退出。

| 检查 | 结果 |
|---|---|
| `colcon build`、接口生成和安装 | 通过 |
| 最新帧缓存、关闭唤醒、非法设备参数 | 3 个 pytest 测试通过 |
| 三个模型真实推理及 ROS 消息往返序列化 | 3 个 pytest 测试通过；检查类别、置信度、检测框、掩膜、时间戳和坐标系 |
| ROS CPU 回放 | s、m、l 全部通过 |
| ROS GPU 回放 | s、m、l 全部通过，设备 `cuda:0` |
| 空实例消息 | 真实图像使用置信度阈值 1.0，节点发布空数组并保留图像信息，通过 |
| SIGINT / SIGTERM 退出 | launch 的 SIGINT 与直接节点的 SIGTERM 检查通过 |
| 1920×1080 GPU 输入 | 真实图像缩放后输入，三个模型各检测到两个 grasper；掩膜尺寸、编码和叠加图通过 |
| 安装后资源查找 | 从源代码目录以外启动三个模型，通过 |

单元测试共 6 个 pytest 用例，由 2 个 CTest 入口执行。`colcon test-result` 汇总显示 8 条测试记录、0 errors、0 failures、0 skipped，包含 CTest 入口记录。

ROS 回放使用真实数据集图像、独立 domain 87，以及上游 `endoscope_device/config/fastdds_local.xml` 的 64 MiB 同机共享内存配置。所有预测均由真实权重产生。

| 依赖 | Ubuntu 实测版本 |
|---|---|
| Python | 3.10.12 |
| Ultralytics | 8.4.190 |
| PyTorch / torchvision | 2.14.1+cu126 / 0.29.1+cu126 |
| NumPy / opencv-python | 1.26.4 / 4.11.0.86 |
| setuptools / packaging | 79.0.1 / 24.2 |
| pytest | 8.3.5 |

证据保存在 `validation/ubuntu/`：`unit-tests.log`、两个 `*.xunit.xml`、`ros-replay-summary.log`、各节点日志及 `core-ubuntu-cuda.json`。

## 验证范围

上游 `endoscope_device` 已拉取至同一工作空间，两个软件包联合编译通过，并确认 ROS 能发现两个包、工作空间自动加载上游 DDS 配置。联合编译记录保存在 `validation/joint/joint-build.log`。设备枚举仅发现笔记本 `Integrated Camera`，上游默认配置对应的 USB 内窥镜尚未连接。

本次验证了编译、真实模型推理和 ROS 数据流。尚未连接实体内窥镜进行联合测试，也未测量实际手术画面的精度、持续运行帧率或端到端延迟。
