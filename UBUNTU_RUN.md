# 已部署的 Ubuntu 环境

- 电脑：Ubuntu 22.04.5 LTS。
- 工作空间：`/home/user/yolofinetune/surgical_perception_ws`。
- 软件包源码：`src/surgical_perception`。
- 上游源码：`src/endoscope_device`，已与感知软件包联合编译通过。
- 环境：工作空间内的 `.venv`，Python 3.10、CUDA 12.6 版 PyTorch。
- 三个模型已通过 CPU 和 RTX 4060 GPU 推理、ROS 图像回放。

## 启动感知节点

在 Ubuntu 终端中执行：

```bash
cd ~/yolofinetune/surgical_perception_ws
source /opt/ros/humble/setup.bash
source .venv/bin/activate
source install/setup.bash
export ROS_DOMAIN_ID=0
export YOLO_CONFIG_DIR="$PWD/work/ultralytics"
export TMPDIR="$PWD/work/tmp"
ros2 launch surgical_perception perception.launch.py model_size:=s device:=cuda:0
```

将 `model_size:=s` 改成 `m` 或 `l` 即可切换模型。按 Ctrl+C 结束。

加载工作空间后，会自动应用上游内窥镜软件包的 Fast DDS 64 MiB 同机共享内存配置。图像发布者和订阅者需要使用一致的 domain 和通信环境。

另开终端，执行相同的环境加载命令，连接上游配置对应的 USB 内窥镜后启动：

```bash
ros2 launch endoscope_device endoscope.launch.py
```

目前设备枚举只发现 `Integrated Camera`，上游配置中的 `usb-DP-251024-J_HD_WebCam-video-index0` 尚未连接，实时硬件联调尚未完成。

没有图像输入时，感知节点等待 `/endoscope/image_raw`。本次没有启动实体摄像头。

## 使用已上传的真实图像检查

另开终端，执行上面相同的环境加载和 export 命令，然后运行：

```bash
python src/surgical_perception/test/ros_replay.py \
  --image test_data/t80_VID54_002160.png
```

脚本发布真实图像，接收实例和叠加图，校验尺寸、时间戳、坐标系和掩膜编码后退出。运行回放时，保持实体内窥镜节点停止，避免同时向同一话题发布两路图像。

实际测试日志位于 `work/results/`，Mac 软件包的 `validation/ubuntu/` 也保存了副本。此次部署保持原有 `/home/user/ros2_ws` 不变。
