#!/usr/bin/env bash
set -eo pipefail

PACKAGE_DIR=$(cd "$(dirname "$0")/.." && pwd)
export SURGICAL_TEST_IMAGE=$(realpath "${1:?请提供包含器械的真实测试图像路径}")
DEVICE=${2:-cpu}
VALIDATION_DIR="$PACKAGE_DIR/work/humble"
mkdir -p "$VALIDATION_DIR"
export YOLO_CONFIG_DIR="$VALIDATION_DIR/ultralytics"
export ROS_DOMAIN_ID=87
source /opt/ros/humble/setup.bash
cd "$VALIDATION_DIR"
colcon build --base-paths "$PACKAGE_DIR" --cmake-args \
  -DBUILD_TESTING=ON \
  -DPython3_EXECUTABLE="$(command -v python3)"
source install/setup.bash
colcon test --packages-select surgical_perception --event-handlers console_direct+
colcon test-result --verbose

node_pid=""
cleanup() {
  if [[ -n "$node_pid" ]] && kill -0 "$node_pid" 2>/dev/null; then
    kill -TERM "$node_pid"
    wait "$node_pid"
  fi
}
trap cleanup EXIT

# 从安装目录以外的位置启动，验证资源查找和真实 ROS 图像收发。
for model in s m l; do
  env --default-signal=INT ros2 launch surgical_perception perception.launch.py model_size:="$model" device:="$DEVICE" \
    > "$VALIDATION_DIR/$model.log" 2>&1 &
  node_pid=$!
  python3 "$PACKAGE_DIR/test/ros_replay.py" --image "$SURGICAL_TEST_IMAGE"
  kill -INT "$node_pid"
  wait "$node_pid"
  node_pid=""
done
printf 'Humble 编译、消息转换、三个模型回放及退出检查通过。\n'
