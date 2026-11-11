from launch import LaunchDescription
from pathlib import Path

import yaml
from launch.actions import DeclareLaunchArgument, OpaqueFunction, Shutdown
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def configure(context):
    path = Path(LaunchConfiguration("config").perform(context))
    values = yaml.safe_load(path.read_text())["surgical_perception"]["ros__parameters"]
    types = dict(image_topic=str, model_size=str, device=str, imgsz=int,
                 confidence=float, publish_overlay=bool)
    # 采用明确的参数类型，防止 CUDA 设备编号被解析成整数。
    return [
        *[DeclareLaunchArgument(name, default_value=str(values[name]).lower()
                               if kind is bool else str(values[name]))
          for name, kind in types.items()],
        Node(
            package="surgical_perception", executable="perception_node",
            name="surgical_perception", output="screen",
            on_exit=Shutdown(),
            parameters=[{
                name: ParameterValue(LaunchConfiguration(name), value_type=kind)
                for name, kind in types.items()
            }],
        ),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("config", default_value=PathJoinSubstitution([
            FindPackageShare("surgical_perception"), "config", "perception.yaml"])),
        OpaqueFunction(function=configure),
    ])
