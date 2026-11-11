# surgical_perception

ROS 2 Humble 手术器械检测与实例分割软件包，接收 `endoscope_device` 的图像，使用 YOLO26-seg 输出器械类别、检测框和逐实例掩膜。

## 环境与模型

- 目标系统：Ubuntu 22.04 x86_64、ROS 2 Humble、Python 3.10；与内窥镜节点同机运行。
- 默认模型：YOLO26s-seg；支持 `s`、`m`、`l` 三种规格。
- 内置权重：`weights/s/best.pt`、`weights/m/best.pt`、`weights/l/best.pt`，来自 CholecInstanceSeg 三次训练的最优模型。
- 类别编号：`0 grasper`、`1 hook`、`2 irrigator`、`3 clipper`、`4 bipolar`、`5 scissors`、`6 snare`。snare 在原验证集和测试集中没有真值实例，其效果尚未得到这两个划分的验证。
- 只提供二维检测与实例分割；不提供跨帧跟踪、三维定位、镜头控制或机械臂控制。

实际验证记录见 [VALIDATION.md](VALIDATION.md)。Mac 上的推理验证与 Ubuntu/Humble 联合验证分别记录。

## 安装与编译

将本目录放入 `~/ros2_ws/src/surgical_perception`。三个最优权重随仓库克隆下载。

在已安装 ROS 2 Humble 的 Ubuntu 22.04 上执行：

```bash
sudo apt update
sudo apt install python3-venv python3-pip python3-colcon-common-extensions \
  python3-rosdep python3-pytest ros-humble-cv-bridge ros-humble-ament-cmake-python \
  ros-humble-rosidl-default-generators ros-humble-ament-cmake-pytest
source /opt/ros/humble/setup.bash
cd ~/ros2_ws
rosdep install --from-paths src/surgical_perception --ignore-src -r -y --rosdistro humble
/usr/bin/python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.14.1 torchvision==0.29.1 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r src/surgical_perception/requirements.txt \
  -r src/surgical_perception/requirements-test.txt
colcon build --packages-select surgical_perception \
  --cmake-args -DPython3_EXECUTABLE="$VIRTUAL_ENV/bin/python3"
source install/setup.bash
```

使用系统 Python 3.10 创建虚拟环境，并保留系统 ROS Python 包。requirements 固定 NumPy 1.26.4 和 OpenCV 4.11，适配 Humble 系统 `cv_bridge` 的 NumPy ABI。编译时记录所选 Python 解释器，运行期间不要移动或删除这个虚拟环境。

以上命令安装 CPU 版 PyTorch。Ubuntu 测试电脑的 RTX 4060 Laptop、驱动 595.99.02 已通过 CUDA 12.6 版 PyTorch 的验证。GPU 环境的安装命令如下，运行时通过 `device:=cuda:0` 选择显卡。指定 CUDA 设备不可用会直接报错。

```bash
python -m pip install torch==2.14.1 torchvision==0.29.1 \
  --index-url https://download.pytorch.org/whl/cu126
```

已经部署好的 Ubuntu 工作空间及启动步骤见 [UBUNTU_RUN.md](UBUNTU_RUN.md)。

## 启动与参数

每个终端都先加载 Humble、Python 环境和同一工作空间：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/.venv/bin/activate
source ~/ros2_ws/install/setup.bash
ros2 launch surgical_perception perception.launch.py
```

模型切换示例：

```bash
ros2 launch surgical_perception perception.launch.py model_size:=m device:=cpu
ros2 launch surgical_perception perception.launch.py model_size:=l device:=cuda:0
```

| 参数 | 默认值 | 含义 |
|---|---|---|
| `config` | 包内 `config/perception.yaml` | 参数文件 |
| `image_topic` | `/endoscope/image_raw` | 图像订阅话题 |
| `model_size` | `s` | `s`、`m` 或 `l` |
| `device` | `cpu` | `cpu`、`0`、`cuda:0` 等单设备选择 |
| `imgsz` | `640` | 预处理目标尺寸，必须是 32 的正整数倍 |
| `confidence` | `0.25` | 置信度阈值，范围 0～1 |
| `publish_overlay` | `true` | 是否允许生成和发布叠加图 |

启动参数覆盖配置文件的对应值。参数在运行期间只读；修改配置后重启。普通安装修改源码配置后需要重新编译，或使用 `config:=/绝对路径/perception.yaml` 指定文件。

推理通过 Ultralytics 完成图像缩放和填充，使用 `retina_masks=True` 返回原图尺寸的掩膜。节点只缓存最新待处理帧，同时最多执行一次推理。推理耗时超过帧间隔时会跳过被替换的画面。

## 与内窥镜节点连接

在另一个加载相同工作空间的终端启动：

```bash
ros2 launch endoscope_device endoscope.launch.py
```

两个节点使用相同的 `ROS_DOMAIN_ID`，并沿用 `endoscope_device` 的 Fast DDS 同机通信环境。本软件包不修改 RMW 或 DDS 环境变量。

输入使用 `sensor_msgs/msg/Image`，转换为 `bgr8`。订阅 QoS 为 `best_effort`、`keep_last`、深度 1，与上游默认配置兼容。上游按需发布原始图像，感知节点订阅后即开始接收。二维推理不依赖相机内参或 TF。

## 输出接口

| 话题 | 类型 | 内容 |
|---|---|---|
| `/surgical_perception/instances` | `surgical_perception/msg/InstrumentArray` | 每帧全部器械实例 |
| `/surgical_perception/overlay` | `sensor_msgs/msg/Image` | `bgr8` 检测与掩膜叠加图 |

输出使用 `best_effort`、`keep_last`、深度 1，订阅端需要兼容该 QoS。话题基于节点私有名称生成，修改节点名称或命名空间会相应改变话题。

`InstrumentArray` 包含原图 `header`、`image_width`、`image_height` 与 `instances`。每个 `InstrumentInstance` 包含：

- `instance_id`：当前帧从 0 开始的编号，不能用于跨帧关联。
- `class_id`、`class_name`、`confidence`：类别及置信度。
- `bbox_xyxy`：原图像素坐标 `[xmin, ymin, xmax, ymax]`，浮点数。
- `mask`：原图尺寸的 `mono8` 图像，背景为 0、实例为 255。每个实例独立存储，保留重叠区域。

数组、掩膜和叠加图均保留对应输入帧的时间戳与 `frame_id`。没有检测到器械时发布空实例数组。叠加图仅在开关打开且有订阅者时生成。节点启动后尚未收到图像时不发布结果。

查看图像与消息定义：

```bash
ros2 run rqt_image_view rqt_image_view /surgical_perception/overlay
ros2 interface show surgical_perception/msg/InstrumentArray
ros2 topic hz /surgical_perception/instances
```

权重缺失、类别不匹配、设备不可用或推理失败时直接报告错误。推理线程异常传回主线程，进程退出；SIGINT/SIGTERM 等待当前推理完成后关闭节点。

## 测试

测试使用真实图像和三个真实权重，不将数据集复制进软件包。选择包含可识别器械的图像。独立推理检查可在安装推理依赖的环境中运行：

```bash
cd ~/ros2_ws/src/surgical_perception
mkdir -p work
PYTHONPATH="$PWD" YOLO_CONFIG_DIR="$PWD/work/ultralytics" \
  python test/validate_core.py --image /绝对路径/真实器械图像.png \
  --package "$PWD" --output work/core.json
```

Humble 自动验证入口：

```bash
source ~/ros2_ws/.venv/bin/activate
bash ~/ros2_ws/src/surgical_perception/test/validate_humble.sh /绝对路径/真实器械图像.png
```

该脚本在包内 `work/humble` 中编译并安装，使用独立 domain 87，验证真实模型消息序列化、最新帧缓存、三个模型的 ROS 回放和退出状态。测试过程中不要在该 domain 启动真实内窥镜节点。日志保存在 `work/humble`。

## 文件与依赖说明

`surgical_perception` 是生成消息的 Python 模块；推理代码安装为 `surgical_perception_runtime`，避免覆盖生成的消息文件。CMake 使用 `ament_get_python_install_dir` 安装运行模块，使用 `rosidl_generate_interfaces` 生成接口。

核心代码依赖 [Ultralytics](https://github.com/ultralytics/ultralytics)，许可证按 AGPL-3.0 提供；模型沿用其来源许可与 CholecInstanceSeg 数据使用条件。此目录只包含部署代码和模型，不包含数据集。
