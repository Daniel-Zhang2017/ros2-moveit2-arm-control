# Hand-Eye Calibration for RoArm-M3 (Eye-in-Hand)

[![ROS2](https://img.shields.io/badge/ROS2-Humble-orange)](https://docs.ros.org/en/humble/)
[![easy_handeye2](https://img.shields.io/badge/easy_handeye2-v0.5.0-blue)](https://github.com/marcoesposito1988/easy_handeye2)
[![OpenCV](https://img.shields.io/badge/OpenCV-Tsai--Lenz-green)](https://opencv.org/)

> 基于 **RoArm-M3 + MoveIt 2 + USB 相机**的 Eye-in-Hand 手眼标定完整方案。使用 `easy_handeye2` 通过 TF 采样和 OpenCV 算法求解相机到末端的静态变换。

**适用场景**：手腕相机（Eye-in-Hand）配置，标定板固定于桌面，机械臂携带相机从多个位姿拍摄标定板。

**前置条件**：已完成相机内参标定，ROS 2 中 TF 树正常发布末端位姿与相机光学坐标系。

---

## 目录

- [前置检查：TF 坐标系确认](#前置检查tf-坐标系确认)
- [快速开始](#快速开始)
- [安装 easy_handeye2](#安装-easy_handeye2)
- [创建标定 launch 文件](#创建标定-launch-文件)
- [准备标定板](#准备标定板)
- [启动标定流程](#启动标定流程)
- [验证标定结果](#验证标定结果)
- [RoArm-M3 特别注意事项](#roarm-m3-特别注意事项)
- [常见问题](#常见问题)
- [参考](#参考)
- [License](#license)

---

## 前置检查：TF 坐标系确认

在启动标定节点前，必须确认以下坐标系名称。启动 RoArm-M3 驱动和相机节点后运行：

```bash
ros2 run tf2_tools view_frames
打开生成的 frames.pdf，记录以下三个关键坐标系：

参数	含义	RoArm-M3 典型值
robot_base_frame	机械臂基座坐标系	base_link 或 world
robot_effector_frame	末端执行器/夹爪坐标系	gripper 或 link5
tracking_base_frame	相机光学坐标系（Z 轴向前）	camera_color_optical_frame 或 camera_link
关键：tracking_base_frame 必须是光学坐标系（遵循 REP 103 右手法则，Z 轴指向相机前方），而不是相机基座坐标系。普通 USB 相机经 usb_cam 发布时通常需要额外配置 optical frame。

快速开始
```bash
# 1. 确认 TF
ros2 run tf2_tools view_frames

# 2. 安装
cd ~/roarm_ws/src
git clone https://github.com/marcoesposito1988/easy_handeye2.git
cd ~/roarm_ws && rosdep install -iyr --from-paths src
colcon build --packages-select easy_handeye2
source install/setup.bash

# 3. 启动标定（使用下方 launch 文件）
ros2 launch roarm_handeye_calibrate.launch.py
安装 easy_handeye2
easy_handeye2 是 ROS 1 easy_handeye 的 ROS 2 移植版，提供 GUI 采样、OpenCV 求解、结果发布与评估的完整功能。

bash
cd ~/roarm_ws/src
git clone https://github.com/marcoesposito1988/easy_handeye2.git

cd ~/roarm_ws
rosdep install -iyr --from-paths src
colcon build --packages-select easy_handeye2
source install/setup.bash
```
创建标定 launch 文件
在 ~/roarm_ws/src 下新建 roarm_handeye_calibrate.launch.py：

```
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    easy_handeye_calibrate = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('easy_handeye2'),
                'launch', 'calibrate.launch.py'
            )
        ),
        launch_arguments={
            'name': 'roarm_m3_wrist_calibration',
            'calibration_type': 'eye_in_hand',
            'robot_base_frame': 'base_link',
            'robot_effector_frame': 'gripper',
            'tracking_base_frame': 'camera_color_optical_frame',
            'freehand_robot_movement': 'true',
        }.items()
    )

    return LaunchDescription([easy_handeye_calibrate])
```

参数说明：

calibration_type='eye_in_hand'：相机装在末端，标定板固定不动。

robot_base_frame / robot_effector_frame：从 TF 树中查到的实际名称，必须完全匹配。

tracking_base_frame：相机光学坐标系名称。

freehand_robot_movement='true'：允许手动移动机械臂采样，适合 RoArm-M3 这类桌面臂。

准备标定板
easy_handeye2 依赖 OpenCV 的 ArUco/ChArUco 检测来获取标定板在相机坐标系下的位姿。你需要：

生成标定板：可使用 OpenCV 官方脚本或 moveit_calibration 自带的 ChArUco 板。

准确测量尺寸：用尺子量出方格边长和标记边长（单位：米），后续检测节点需要这些参数。

打印并贴平：必须贴在硬质平板（泡沫板或铝板）上，纸张弯曲会导致检测失败、标定结果错误。

固定于桌面：标定板在工作区中央保持静止，确保机械臂移动时始终在相机视野内。

如果你没有现成的 ArUco 检测节点，可以使用 aruco_ros 包发布标定板位姿。

启动标定流程
需要三个终端：

终端 1：启动 RoArm-M3 驱动
```bash
cd ~/roarm_ws
source install/setup.bash
export ROARM_MODEL=roarm_m3
ros2 run roarm_driver roarm_driver
```

终端 2：启动相机节点

```bash
# 示例：usb_cam
ros2 run usb_cam usb_cam_node_exe --ros-args \
  -p video_device:=/dev/video0 \
  -p image_width:=640 \
  -p image_height:=480 \
  -p framerate:=30.0 \
  -p camera_info_url:=file:///path/to/your/camera_calibration.yaml
```
必须加载相机内参。如果相机节点不发布正确的 camera_info，标定板位姿会包含畸变误差，导致手眼标定失败。

终端 3：启动手眼标定

```bash
ros2 launch roarm_handeye_calibrate.launch.py
```

RViz 中的采样操作
RViz 会打开，显示机械臂模型、相机图像和 easy_handeye2 面板。

确认标定板在相机图像中被稳定检测（能看到检测到的标记和位姿）。

用 MoveIt 或键盘控制 RoArm-M3，让相机从不同角度、不同距离拍摄标定板。

每个位姿下点击 "Take Sample"。建议采集 15–20 组，覆盖位置和旋转的多样性。

采够后点击 "Compute"。结果会自动保存并发布为 TF。

采样技巧：不要只在同一位置小幅度晃动。让标定板出现在画面的不同区域（左、右、上、下、远、近），并尝试不同的倾斜角度。

验证标定结果
easy_handeye2 提供了评估 launch：

```bash
ros2 launch easy_handeye2 check.launch.py \
  name:=roarm_m3_wrist_calibration \
  calibration_type:=eye_in_hand
```

在 RViz 中观察标定板在机器人基座坐标系下的位姿：

正常：标定板位姿稳定，位置与桌面实际位置一致，不随机械臂移动而漂移。

异常：标定板位姿乱跳或明显偏离桌面 → 采样数据质量不足，需要增加位姿多样性后重新标定。

实际抓取验证
标定完成后，让相机观测一个已知位置的点（如桌面上的标记），用标定矩阵计算出机械臂应到达的坐标，实际移动过去观察偏差。RoArm-M3 的舵机精度有限，不要期望毫米级精度，偏差稳定在合理范围内即可接受。

## RoArm-M3 特别注意事项

### 1. 相机内参必须先标定

手眼标定依赖相机内参去除畸变。如果还没做，先用 `camera_calibration` 标定：

```bash
ros2 run camera_calibration cameracalibrator \
  --size 8x6 --square 0.025 \
  --ros-args -r image:=/usb_cam/image_raw -r camera:=/usb_cam

采集 30–40 张覆盖画面各区域的棋盘格图像，保存 YAML 并在启动相机时加载。
```

### 2. TF 坐标系名称必须完全匹配

easy_handeye2 通过 TF 采样，任何名称不匹配都会导致采样失败。启动标定前务必用 view_frames 确认三个坐标系的实际名称。RoArm-M3 的 URDF 中末端坐标系可能是 link5 而非 gripper，以实际 TF 树为准。

### 3. 精度预期要现实

RoArm-M3 是舵机驱动的桌面臂，重复定位精度和刚性远不及工业机械臂。手眼标定提供的是合理的初始变换，实际抓取任务中建议加入视觉伺服微调（基于图像误差的小范围调整），而不是完全依赖标定矩阵做开环抓取。

### 4. 标定板检测链路

easy_handeye2 本身不检测标定板，它只负责采样和求解。你需要确保相机图像中有节点在发布标定板的位姿 TF。如果使用 aruco_ros，确认 marker 尺寸参数与实际打印尺寸一致。

**常见问题**

标定板检测不到 / 位姿跳变
检查光照是否均匀，避免反光或过暗。

确认 aruco_ros 或检测节点的 markerSize 参数与实际测量值一致（单位：米）。

标定板是否贴平？纸张弯曲会导致检测失败。

采样时 TF 报错 "Lookup would require extrapolation"
检查 RoArm-M3 的 roarm_driver 和相机节点是否都在正常运行。

确认 TF 树中 robot_effector_frame 到 robot_base_frame 的链路完整。

**标定结果偏差大**

增加采样数量到 20 组以上，增加位姿多样性。

检查相机内参是否准确加载（camera_info 是否正确发布）。

确认标定板尺寸测量准确。

### Compute 后结果不保存

`easy_handeye2` 默认将标定结果保存在 `~/.ros2/easy_handeye2/calibrations/` 下。确认该目录有写入权限。

---

## 参考

- [easy_handeye2 GitHub](https://github.com/marcoesposito1988/easy_handeye2) — ROS 2 手眼标定框架
- [MoveIt Calibration Tutorial](https://moveit.github.io/moveit_tutorials/doc/hand_eye_calibration/hand_eye_calibration_tutorial.html) — Eye-in-Hand 标定流程与标定板生成
- [aruco_ros](https://github.com/pal-robotics/aruco_ros) — ArUco 标记检测与位姿发布
- [RoArm-M3 ROS2 教程](https://docs.waveshare.net/RoArm-M3/ROS2-tutorial/) — 驱动启动与 TF 配置

---

> **"眼睛标定"**（相机内参标定）解决的是"相机怎么看"的问题；而**完整的手眼标定**解决的是"相机看到的东西，和机械臂的手（末端）是什么位置关系"的问题。

> **"手"在标定里的具体角色**：在 Eye-in-Hand 配置下，标定要解出的那个变换矩阵，就是**相机坐标系到机械臂末端坐标系的固定转换关系**。这个关系之所以能算出来，是因为你让机械臂（手）动了起来。标定过程中，机械臂带着相机移动到多个不同的位姿，每到一个位置，系统就会记录两个数据：
>
> - **手的位姿**：机械臂末端在基座坐标系下的位置和姿态（从 ROS TF 或 MoveIt 中读取）。
> - **眼的观测**：相机看到的标定板在相机坐标系下的位姿（通过识别标定板图像计算得出）。
>
> 有了多组这样的"手眼"对应数据，算法（如 `easy_handeye2` 内部调用的 Tsai-Lenz 或对偶四元数方法）就能解出那个固定的相机-末端变换矩阵。

License
Apache 2.0
