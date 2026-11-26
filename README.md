# 6-DoF Robotic Arm ROS 2 + MoveIt 2 Stack + Arm Hand Gesture Teleoperation + Using the roarm_m3 with LeRobot

[![LeRobot](https://img.shields.io/badge/LeRobot-v0.6+-blue)](https://github.com/huggingface/lerobot)
[![Python](https://img.shields.io/badge/Python-3.12+-green)](https://www.python.org/)
[![ROS2](https://img.shields.io/badge/ROS2-Humble-orange)](https://docs.ros.org/en/humble/)
[![MoveIt2](https://img.shields.io/badge/MoveIt_2-Humble-brightgreen)](https://moveit.ai/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-red)](https://opencv.org/)
[![C++](https://img.shields.io/badge/C++-17-blue.svg)](https://isocpp.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A complete ROS 2 Humble workspace for a 6-joint manipulator with a parallel gripper, including the robot description, MoveIt 2 planning configuration, hardware bringup, hand-eye calibration, a custom C++ motion commander, MoveIt 2 MTC (MoveIt Task Constructor), custom ROS 2 interfaces (using both ros2 topic and action communication) & pipeline (**using your own arm control commands rather than the code from the arm manufacturer**), **Singularity handling**, Arm Hand Gesture Teleoperation and **using the roarm_m3 with Lerobot**.

>In an actual robotic arm system, other ROS 2 nodes can send joint targets, end-effector poses, or grasping tasks to the **Commander node via topics, services, or actions**. 

>The **Commander node** calls MoveIt 2 through the MoveIt API to perform kinematics computation, collision detection, and trajectory planning. The resulting joint trajectory is then sent through the MoveIt controller to the trajectory controller in ros2_control, which further converts it into control commands for the real robotic arm or simulated hardware. During hardware execution, state information such as joint positions and velocities is continuously returned; ros2_control publishes these states as joint states, and robot_state_publisher then publishes TF coordinate transforms in combination with the URDF model, allowing MoveIt and RViz to obtain the current robot pose.
> **Arm Hand Gesture Teleoperation**：Package: `my_robot_commander_cpp`：This package provides hand-gesture teleoperation for a robotic arm controlled by MoveIt2. There are two independent Python teleoperation frontends sharing the same C++ commander backend:

> - `hand_gesture_arm_action_ctl.py`: uses a ROS2 Action server to send arm motion goals
> - `hand_gesture_arm_topic_ctl.py`: uses ROS2 topics, throttled to 5 Hz for pose commands
> -Hand tracking is implemented with MediaPipe Hand Landmarker.

**Cartesian force-controlled surface follower for the Franka Panda arm; please see my other repo.**
[wall_climb_force_compliance_robot](https://github.com/Daniel-Zhang2017/wall_climb_force_compliance_robot)

>
## video demos

*Video 1: Arm motion demo, recorded at 100 Hz joint states: ros2 bag record /joint_states*

https://github.com/user-attachments/assets/a827dda0-dc04-47a8-88f3-8c268dc0bbe3

*Video 2: Roarm control and motion: Cartesian path*

https://github.com/user-attachments/assets/c8ac123a-d9f0-467d-afe4-b9e7536e7b07

*Video 3: Real arm Cartesian path*

https://github.com/user-attachments/assets/b6f72d57-6e1e-4b73-a8a3-074690e890e5

*Video 4: Real robotic arm control and motion*

https://github.com/user-attachments/assets/7caf02ca-e448-450b-a686-7556f6876fa5

*Video 5: Panda_moveit_avoid_collision*

https://github.com/user-attachments/assets/13b10d0f-8d62-40c9-ade0-d3b75a0c3b4d

*Video 6: Panda_moveit pick and place*

https://github.com/user-attachments/assets/c0fe0ebf-7c51-49d2-b423-7d7f966c1ba7

**Robotic Arm Control System Architecture**
```
1. Robot Modeling Layer
First, use URDF and Xacro to describe the links, joints, motion ranges, collision models, and mounting relationships of the robotic arm and gripper, forming a digital structural model of the robot. This model answers questions such as "what is the robot composed of, how can each joint move, and where is the end effector located." Subsequently, robot_state_publisher publishes TF coordinate transforms based on the URDF model and joint states, and RViz displays the current pose of the robotic arm accordingly. Therefore, URDF is responsible for defining the structure, joint_states reflects the current joint states, and TF and RViz are responsible for visualizing the states.

2. Motion Planning Layer
At the motion planning layer, the MoveIt Setup Assistant is used to configure the arm planning group, gripper planning group, end effector, named poses, collision matrix, joint constraints, and controller mapping. MoveIt's role is to compute a feasible joint motion trajectory based on the robot model, target state, and collision constraints. It does not directly drive the motors; rather, it is responsible for answering "what path should the robotic arm follow to safely reach the target."

3. Trajectory Execution Layer
At the trajectory execution layer, the project uses ros2_control to establish a standard connection between the controllers and the hardware. controller_manager is responsible for managing the controllers, joint_state_broadcaster is responsible for publishing joint states, and arm_controller and gripper_controller are responsible for receiving trajectories and executing joint control. The current system uses FakeSystem as the simulated hardware; it does not connect to real motors but instead simulates the process of hardware receiving commands and returning states. Therefore, the trajectories planned by MoveIt can be executed in RViz and update the robot pose. When connecting to a real robotic arm later, the main task is to replace FakeSystem with the corresponding vendor's hardware interface and driver, while the upper-layer planning and Commander control logic can remain largely unchanged.

4. Upper-Layer Task Control
In the upper-layer task control part, the project implements a Commander node based on the MoveIt C++ API. This node encapsulates robotic arm control into functions such as named pose control, joint angle control, end-effector pose control, Cartesian path control, and gripper open/close control, and receives external commands via ROS 2 topics. External nodes can publish joint targets, gripper open/close commands, or end-effector pose targets; after receiving the messages, the Commander calls MoveGroupInterface to set the target, request MoveIt planning, and execute the trajectory. In this way, upper-layer vision, task planning, or human interaction modules do not need to directly operate the controllers; they only need to send task targets to the Commander.

5. Overall Control Chain
The control chain of the entire project can be summarized as:

External task node or terminal
→ Publish joint, pose, or gripper control commands
→ Commander node receives and calls the MoveIt C++ API
→ MoveIt plans the trajectory based on the model, constraints, and collision information
→ MoveIt sends the trajectory to the controllers in ros2_control
→ arm_controller or gripper_controller controls FakeSystem
→ FakeSystem returns joint states
→ joint_state_broadcaster publishes joint_states
→ robot_state_publisher publishes TF based on URDF
→ RViz and MoveIt obtain the current robot pose and complete visualization.

This can be simplified into two chains:

Control chain:
Other nodes → Commander → MoveIt → ros2_control → Hardware

State feedback chain:
Hardware → ros2_control → joint_states → robot_state_publisher → TF → MoveIt / RViz
```
```
#installation dependencies
sudo apt update
sudo apt install ros-humble-moveit ros-humble-moveit-ros-planning-interface
```
```
git clone https://github.com/Daniel-Zhang2017/ros2-moveit2-arm-control.git
cd ros2-moveit2-arm-control
colcon build
source install/setup.bash
```

## Repository Structure
```
src/
├── my_moveit_config          # Primary MoveIt 2 configuration (SRDF, kinematics, controllers, launchers)
│   ├── config/               # SRDF, URDF/xacro, kinematics.yaml, joint limits, controller params, RViz config
│   └── launch/               # auto-generated MoveIt launch files (move_group, demo, rsp, spawn controllers)
├── my_robot_bringup          # System bringup package (master launch file)
│   ├── config/               # RViz config + ros2_control controller yaml
│   └── launch/my_robot.launch.xml  # Main entry launch: robot_state_publisher + ros2_control + move_group + RViz
├── my_robot_commander_cpp    # C++ MoveGroupInterface motion commander node (this is your control program)
│   └── src/
│       ├── commander_template.cpp  # Main commander node: topic-controlled arm + gripper
│       ├── commander_action.cpp  # Main commander node: action-controlled arm + gripper
│       ├── test_moveit.cpp
│       └── test2_moveit.cpp
│       └── scripts/
│             └── hand_gesture_arm_action_ctl.py    # Action-based teleop
│             └── hand_gesture_arm_topic_ctl.py     # Topic-based teleop (5 Hz)
│             └── hand_landmarker.task              # MediaPipe hand landmarker model
├── my_robot_description      # Robot URDF / Xacro model
│   ├── urdf/                 # Arm, gripper, common properties, ros2_control xacro
│   └── launch/display.launch.xml  # Quick URDF visualization only
├── my_robot_interfaces       # Custom ROS 2 message definitions
│   └── msg/PoseCommand.msg   # Custom pose command with RPY + Cartesian flag
│   └── action/ArmCommand.action   # Custom action interface
├── my_arm_config       # Custom arm config for Roarm
├── roarm_description       # roam URDF/Xacro model
├── roarm_driver       # roam driver
├── roarm_moveit       # roarm MoveIt, the code from the arm manufacturer

```

## System Overview
This stack implements a standard `ros2_control` + MoveIt 2 pipeline:
1. `my_robot_description`: Kinematic model of 6DoF arm + gripper, with ros2_control transmission tags
2. `my_moveit_config`: MoveIt setup: semantic SRDF, KDL kinematics solver, joint limits, OMPL planner
3. `my_robot_bringup`: Single XML launch file to start the whole control stack
4. `my_robot_commander_cpp`: High-level C++ commander node that wraps `MoveGroupInterface`
   - Supports named SRDF poses, joint targets, pose targets (normal planning / Cartesian straight line)
   - Topic-based runtime control for arm and gripper
5. `my_robot_interfaces`: Custom `PoseCommand` message for end-effector pose goals
6. `my_arm_config`: use a standard `ros2_control` + MoveIt 2 pipeline config, rather than using the manufacturer's code
7. `roarm_description`: roarm URDF/Xacro model
8. `roarm_driver`: roarm URDF/Xacro model
9. `roarm_moveit `: roarm MoveIt code from the arm manufacturer


## Key Packages Detail
### `my_robot_description`
Robot model built with modular XACRO:
- `arm.xacro`: 6 revolute joints of the manipulator
- `gripper.xacro`: Parallel gripper
- `common_properties.xacro`: Inertial, material, collision geometry
- `my_robot.ros2_control.xacro`: ros2_control hardware interface definitions

Quick visual check (no MoveIt):
```bash
ros2 launch my_robot_description display.launch.xml
```

### `my_moveit_config`

Auto-generated from MoveIt Setup Assistant, extended with `kinematics.yaml` for KDL IK:

- `my_robot.srdf`: Virtual joints, collision disabled pairs, named group states (`home`, `pose_1`, `gripper_open`, `gripper_closed`)
- `kinematics.yaml`: KDL kinematics plugin config for `arm` and `gripper` planning groups
- `ros2_controllers.yaml`: `arm_controller` (joint trajectory), `gripper_controller`, `joint_state_broadcaster`
- Launchers: `move_group.launch.py` is included by the bringup file

### `my_robot_bringup`

**Main entry point of the robot stack**
`my_robot.launch.xml` starts:

- robot_state_publisher (load xacro robot description)
- ros2_control_node
- Spawners for joint_state_broadcaster, arm_controller, gripper_controller
- Include `move_group.launch.py` from `my_moveit_config`
- RViz2 with MoveIt config

Start full stack:

```
ros2 launch my_robot_bringup my_robot.launch.xml
```

### `my_robot_commander_cpp`

C++ MoveIt2 commander node (`commander_template.cpp`) for robotic arm + gripper control.
It instantiates two independent `MoveGroupInterface` planners: `arm` and `gripper`.
Supports joint-space, named-pose, standard MoveIt planning and local Cartesian straight-line planning, plus end-effector pose feedback.

## Topics

### Subscribed

| Topic | Message Type | Description |
| --- | --- | --- |
| `/open_gripper` | `example_interfaces/msg/Bool` | `true` = open gripper; `false` = close gripper |
| `/joint_command` | `example_interfaces/msg/Float64MultiArray` | 6 joint angles for the arm (joint-space target) |
| `/pose_command` | `my_robot_interfaces/msg/PoseCommand` | Pose target: `x, y, z, roll, pitch, yaw, cartesian_path` |

### `my_robot_interfaces`

Custom message `PoseCommand.msg`:

```
float64 x
float64 y
float64 z
float64 roll
float64 pitch
float64 yaw
bool cartesian_path
```

Custom action `ArmCommand.action`:

```
# goal
uint8 command_type
float64[] joint_target
float64 x
float64 y
float64 z
float64 roll
float64 pitch
float64 yaw
bool cartesian_path
string named_target
bool gripper_open
---
# feedback
float64 progress
string status_msg
---
# result
bool success
string message
```

## Build Instructions

Install Python dependencies:

```bash
pip3 install mediapipe opencv-python
```
Build all packages in your ROS 2 workspace:
```
colcon build --packages-select my_robot_description my_moveit_config my_robot_bringup my_robot_interfaces my_robot_commander_cpp
source install/setup.bash
```

## Run
```
ros2 launch my_robot_bringup my_robot.launch.xml
```
```
# Launch your MoveIt stack first with use_sim_time:=true; this is using ros2 topic-control the arm and gripper
ros2 run my_robot_commander_cpp commander_template --ros-args -p use_sim_time:=true
```

```
# This is using ros2 action-control the arm and gripper (Better than topic-control)
ros2 run my_robot_commander_cpp commander_action --ros-args -p use_sim_time:=true
```

> 
> Important: your MoveIt launch must also pass `use_sim_time:=true` for simulation clock alignment.
> 

### Send runtime commands via CLI for ros2 topic-control the arm and gripper

```
# Open gripper
ros2 topic pub /open_gripper example_interfaces/msg/Bool "{data: true}"

# Close gripper
ros2 topic pub /open_gripper example_interfaces/msg/Bool "{data: false}"

# Send 6 joint target (radians)
ros2 topic pub /joint_command example_interfaces/msg/Float64MultiArray "{data: [0, -0.785, 1.57, -0.785, 0, 0]}"
```

### Send runtime commands via CLI for ros2 action-control the arm and gripper

#### Gripper open

```
ros2 action send_goal /arm_command my_robot_interfaces/action/ArmCommand "
command_type: 4
gripper_open: true
"
```

#### Gripper close

```
ros2 action send_goal /arm_command my_robot_interfaces/action/ArmCommand "
command_type: 4
gripper_open: false
"
```

#### Move to named target

```
ros2 action send_goal /arm_command my_robot_interfaces/action/ArmCommand "
command_type: 3
named_target: home
"
```

#### Joint target

```
ros2 action send_goal /arm_command my_robot_interfaces/action/ArmCommand "
command_type: 1
joint_target: [0.0, -1.57, 0.0, -1.57, 0.0, 0.0]
"
```

#### Cartesian pose (normal IK)

```
ros2 action send_goal /arm_command my_robot_interfaces/action/ArmCommand "
command_type: 2
x: 0.4
y: 0.0
z: 0.3
roll: 0.0
pitch: 0.0
yaw: 0.0
cartesian_path: false
"
```

### Cartesian straight line

```
ros2 action send_goal /arm_command my_robot_interfaces/action/ArmCommand "
command_type: 2
x: 0.4
y: 0.0
z: 0.3
roll: 0.0
pitch: 0.0
yaw: 0.0
cartesian_path: true
"
```

#### Check / Debug

```
ros2 action list
ros2 action info /arm_command
```

#### Action Definition Mapping
>`command_type`:
> - `1` → joint target
> - `2` → Cartesian pose
> - `3` → named target
> - `4` → gripper control

> Feedback:
> - `success`: bool
> - `message`: string

> Result:
> - `progress`: double
> - `status_msg`: string

### ROS2 MoveIt2 Arm Hand Gesture Teleoperation

#### Action version

```
ros2 run my_robot_commander_cpp hand_gesture_arm_action_ctl.py
```

#### Topic version (5 Hz throttled)

```
ros2 run my_robot_commander_cpp hand_gesture_arm_topic_ctl.py
```

Press `q` in the OpenCV preview window to exit the Python teleop node.

#### Notes

- Units: meters, radians
- `cartesian_path: true` uses `computeCartesianPath`; may fail if the straight path is not reachable
- The server rejects a new goal if one is already active
- Calling stop on cancel request

**Capture the RViz window into `raw_capture.mp4`**

> Step 1: Capture RViz window (new terminal)

> First find the window ID of RViz:

```
xwininfo
```
>Then click your RViz window. You will see something like: xwininfo: Window id: 0x5800004 "RViz"

>Copy that Window ID number (e.g. `0x5800004`). Run capture (replace `0x5800004` with your own window id):

```
ffmpeg -y -f x11grab -window_id 0x5800004 -framerate 30 -i :0.0 raw_capture.mp4
#- `-framerate 30`: capture at 30fps
#- Press `q` in this ffmpeg terminal to stop recording.
```

To be added:

一是一个可在 Humble/Jazzy 跑的极简 ROS2 RCM 约束节点（Python 或 C++），

二是 MoveIt2 + `moveit_servo` 做软件 RCM 的 launch + 配置流程

----------------------------------------------------------------------------------------------------------------------------------------

# Notes for learners: 

1. The core difference between Python and XML launch files in ROS 2 lies in flexibility versus declarative simplicity. Python offers powerful programming capabilities and lower-level access, making it suitable for complex logic; XML is more concise and declarative, making it suitable for simple, straightforward startup tasks and users migrating from ROS 1.

2. MoveIt 2 is a widely used motion planning framework in ROS 2. It is responsible for generating motion trajectories based on robot models, joint limits, collision information, and target states, though it does not directly control the motors.

3. Configure a robotic arm visually using the MoveIt Setup Assistant

MoveIt Setup Assistant (MSA) — Description

> **MoveIt Setup Assistant** is the official GUI wizard tool for MoveIt 2 (ROS 2 Humble/Iron/Jazzy), used to **generate all required MoveIt configuration packages from your robot URDF/Xacro**. It automates the tedious YAML / SRDF / controller config creation, so you can quickly get your manipulator ready for planning, RViz demo, ros2_control and execution.

> A planning group defines a collection of joints and links that MoveIt will treat as a single controllable kinematic subsystem, such as a robotic arm or gripper. Each planning group is assigned an inverse kinematics solver, search parameters and a default motion planner.

> **Inverse Kinematics (IK)** solves the problem:
>
> Given a desired end-effector Cartesian pose (position + orientation in 3D space), calculate the corresponding set of joint angles for your robot arm.

> Forward kinematics does the opposite: input joint angles → compute end-effector pose.

```bash
ros2 launch moveit_setup_assistant setup_assistant.launch.py
```
In the RViz2 Motion Planning panel:

>Set goal (drag interactive marker or joint slider), or adjust Start State, Goal State under the Planning/Query

>Click Plan → preview path drawn, robot stays still

>Then click Execute → robot moves. Or directly click Plan & Execute to combine two steps

>Rviz motion planning/scene objects panel: The Scene Objects panel in the MoveIt RViz Motion Planning plugin is where you manage the collision environment. You use it to add, move, attach, or remove objects that the robot must avoid during motion planning.

MoveGroupInterface is the core C++ API class in MoveIt2 (header: moveit/move_group_interface/move_group_interface.h).

>It acts as a high-level wrapper to communicate with the move_group node.

>You use it to command a robot planning group: set target pose / joint goal, run motion planning, execute trajectory, query robot state, perform Cartesian path planning, etc.

✅ In short:

>MoveGroupInterface = the main C++ bridge between your user program and the MoveIt move_group server.

>It hides the low-level ROS service / action calls, so you do not manually send action goals.

After finishing the setup in the MSA, you need to check moveit_controllers.yaml and add the following code:
```
action_ns: follow_joint_trajectory
default: true
```
> 📌 Concept:
> MoveIt (client) sends trajectory goal → calls this Action Server.
> The action type is `control_msgs/action/FollowJointTrajectory`
> 
> 
> If you **do NOT write `action_ns`**, the plugin uses the **default value which IS already `follow_joint_trajectory`**
> → So it is optional, only needed when your real controller uses a **custom action name** (uncommon).

 ✅ `default: true`

**Mark this controller as the DEFAULT controller**

- When MoveIt TrajectoryExecutionManager picks a controller for your joints, if multiple controllers can cover the same joints, the one with `default: true` has priority


4. Comparison: PTP Joint Planning vs Cartesian Planning

| Feature | PTP Joint Space Planning | Cartesian Path Planning |
|---|---|---|
| Trajectory control | Only start & goal joint states | End-effector TCP path |
| End-effector path | Curved, uncontrolled | Near straight line |
| Computation cost | Low | High (IK at every sample) |
| Singularity risk | Low | High |
| Use cases | Pick & place, point reaching | Welding, grinding, dispensing, assembly |

**5. Safety Warning**

>Do NOT set jump_threshold = 0 on a real robot.

>Cartesian IK may switch to a different joint solution and cause sudden, unsafe large joint motion.

>Always perform full simulation validation and enable collision checking before real robot operation.

# Real robotic arm control and motion

roarm_driver.py:  A **simple ROS 2 bridge node** between ROS2 `JointState` messages and the Waveshare RoArm SDK serial API.

> 
> Core logic: It **subscribes to `/joint_states`**, extracts joint angles, repacks them into the order the RoArm hardware expects, then sends them over USB serial to the physical arm.
> 
> 
> ⚠️ Important design note: This is **not a standard ros2_control hardware interface**. This is a custom, lightweight driver that directly consumes `JointState` topics.

Grant read and write permissions to the serial device using the following command (replace /dev/ttyUSB0 with your actual device path):
```
sudo chmod 666 /dev/ttyUSB0
```
Run the driver node:
```
ros2 run roarm_driver roarm_driver serial_port:=/dev/ttyUSB0
```
🚨 **This is the root architectural quirk you need to understand:**
>Standard ros2_control pipeline:

>`MoveIt → ros2_control controller (hand_controller) → hardware_interface → send command to robot`

>But this driver’s pipeline is:

>`MoveIt → hand_controller → controller publishes /joint_states (target) → THIS NODE SUBSCRIBES /joint_states → send serial command to >RoArm`

>So the `hand_controller` (joint_trajectory_controller) outputs target positions as `/joint_states`, then this driver picks it up and forwards to hardware.

## MTC solves complex manipulation tasks by splitting the job into composable `Stage`s. 

Instead of one-shot motion planning, MTC explores alternative solution branches, backtracks on failure, and manages `PlanningScene` states (attach/detach objects) automatically.

> Paper: *MoveIt! Task Constructor for Task-Level Motion Planning*, ICRA 2019

📌 **What is MTC?**

>MTC is a task planning framework built on top of MoveIt2.

>- Decompose manipulation into serial/parallel stages

>- Pass `InterfaceState` between stages: robot state, planning scene, collision objects, candidate solutions

>- Automatic backtracking: if one grasp/plan fails, try the next candidate

>- Native support for `attach` / `detach` for pick-and-place

- RViz MTC plugin for visual debugging of all candidate branches and costs

Three core stage types:

>1. **Generator**: Generate candidate solutions (e.g. `GenerateGraspPose`)
>2. **Propagator**: Transform state (MoveTo, MoveRelative, ModifyPlanningScene)
> 3. **Connector**: Plan motion between two states (`Connect`)

>Containers: `Serial`, `Parallel` to build task graphs.

## Pick and Place with MoveIt Task Constructor

It demonstrates how to chain multiple planning stages (pick, transport, place) into a single task using MoveIt Task Constructor (MTC), execute it on the Panda robot, and visualize the result in RViz.

>Note: This is based on the MoveIt 2 Humble documentation (a stable, no-longer-developed release). For the current recommended version, see MoveIt Main.

>https://moveit.picknik.ai/humble/doc/tutorials/pick_and_place_with_moveit_task_constructor/pick_and_place_with_moveit_task_constructor.html

## Using the roarm_m3 with LeRobot

check lerobot_solutions/

## Related Projects

- [wall_climb_force_compliance_robot](https://github.com/Daniel-Zhang2017/wall_climb_force_compliance_robot) - Manipulator constant normal force compliance (force control) on planar wall, with bump adaptation & force-based E-Stop. Built on ROS2, Rviz2, MuJoCo, MoveIt2, Movelt Servo. Control Algorithm Comparison (Wall-Following Force Control): P, PID, Python-based CVXPY MPC, Acados MPC. Suitable for facade inspection / cleaning / surface contact task prototype.

- [roarm_ws](https://github.com/Daniel-Zhang2017/roarm_ws) — real arm control and motion

- [ros2-robotics-projects](https://github.com/Daniel-Zhang2017/ros2-robotics-projects) — autonomous mobile robots and robotic arms

## Notes for learners

1.**Mimic Joint & Gripper Debug Note**
- A `<mimic>` joint in URDF / Xacro is a **passive, coupled joint**. It does not receive its own independent command. Its position is mathematically slaved to another “master” joint:

```
<joint name="slave_joint" type="prismatic">
  <mimic joint="master_joint" multiplier="-1.0" offset="0.0"/>
</joint>
```

In **ros2-moveit2-arm-control/src/my_robot_description/urdf/gripper.xacro**, there is a commented line:

```xml
<!-- <mimic joint="gripper_left_finger_joint" multiplier="-1.0"/> -->
```
Note: If you are using a mimic joint, uncomment this line.

**Debug Checklist**

□ Direct ros2 action success only verifies the controller itself, not MoveIt integration.

□ Ensure URDF joint definition, ros2_control controller joints, MoveIt controller joints, and SRDF group are consistent.

□ Do not assign an IK solver to the gripper group.

2. **When Action fits**

ROS 2 Action is designed for long-running goals with:

- a goal request (target pose / joint target / gripper command)
- periodic feedback
- a final result (success / failure code)
- explicit cancel

That matches robotic arm motion very well. A caller can:

- send a motion goal
- receive feedback during movement
- wait for success or failure
- cancel the goal if needed

This aligns naturally with MoveIt’s “plan then execute” workflow.

**But: Action is not always the only choice**

You can still keep topics for these cases:

- High-frequency streaming setpoints, e.g. teleop jogging, impedance control, continuous velocity commands.
- State observation: publish actual joint state, end-effector pose, status.

The bad fit is using one-shot topic messages as “execute this planned motion command”.

3. ## Singularity handling and Safety boundary

MoveIt2 分两条路线：**Move Group 预规划** 和 **MoveIt Servo 实时伺服**，二者能力不一样。

### A. MoveIt Servo（实时 teleop / Cartesian twist）

Servo 是最直接做奇异点在线处理的模块：它通过雅可比矩阵的条件数（condition number）判断是否靠近奇异；条件数变大代表雅可比接近奇异、末端微小运动对应关节大速度。参数在 `servo_parameters.yaml` 配置：

- `lower_singularity_threshold`：进入该阈值开始自动减速缩放速度
- `hard_stop_singularity_threshold`：达到该阈值直接停止伺服
- `leaving_singularity_threshold_multiplier`：离开奇异区时用更高阈值，防止在边界反复抖动[MoveIt 2](https://moveit.picknik.ai/humble/api/html/servo__parameters_8cpp_source.html?f_link_type=f_linkinlinenote&flow_extra=eyJkb2NfaWQiOiJkMTFlM2M0ZTQ2NGIzNGFjLWY0ZjQzNjRiNWRkZWRmNTUiLCJpbmxpbmVfZGlzcGxheV9wb3NpdGlvbiI6MCwiZG9jX3Bvc2l0aW9uIjowfQ%3D%3D)

Servo 的行为是**限速–减速–停机**，不是自动绕开奇异；IK 可以走 Jacobian 逆或者配置 IK plugin。

### B Move Group / MTC 预规划

原生 OMPL 等通用规划器**没有专门的 “奇异点检测器”**。做法是：

- 依赖 IK 求解器返回可行解，尽量不采样奇异构型；
- 加入 kinematic constraints、joint limits、软限位，把危险区域排除；
- 对 Cartesian path，使用 Pilz Industrial Motion Planner，它支持 Cartesian limits，适合直线轨迹；
- 评估轨迹时额外校验雅可比条件数，在应用层 reject 或重规划；
- 选择冗余解：很多 IK 可以返回多个解，规划时挑选远离奇异的关节构型。

### 补充工程手段

- 预标定机器人奇异位姿表，在状态机里增加禁区；
- 设计任务几何，尽量让操作路径避开 wrist singularity、shoulder singularity；
- 力控辅助：靠近奇异时切换到关节空间控制，或者降低 Cartesian 增益；
- 自己写回调约束：`moveit_msgs/Constraints` + 自定义 validity checker。

## Safety boundary

安全边界是多层叠加，MoveIt2 本身是软件层，不是替代硬件急停。

### Joint‑space boundary

- URDF / SRDF 写硬关节位置范围；
- joint limits yaml 配置位置、速度、加速度、jerk；
- soft joint limits：提前减速缓冲，避免冲到硬限位；
- Servo 的 `joint_limit_margin`：给限位预留安全余量，靠近时降速。

### Cartesian / workspace boundary

MoveIt 支持几种方式：

- `PositionConstraint`：把末端或某 link 限制在一个空间区域（box /sphere 等），规划器会校验；
- Pilz planner 的 Cartesian limits，限制末端速度、路径范围；
- 把静态安全盒 / 平面加到 planning scene（`planning_scene` collision object），规划和 Servo 碰撞检查会避开；
- 应用层监控：持续读取 end‑effector pose，越界则 cancel trajectory、停止 Servo、触发保护；
- 对手术机器人：额外定义 sterile volume、禁止进入区，在仿真 + 台架测试验证。

### Collision and runtime safety

- Servo 自带 proximity‑based collision scaling：靠近自碰撞或场景物体时减速；
- Move Group 规划时默认做碰撞检查；
- 外部叠加：ros2_control 层限位、硬件急停、力阈值 E‑Stop、超时保护（Servo `incoming_command_timeout`）；
- 日志、状态上报、故障响应流程，符合医疗设备验证习惯。

> 4. ## RCM

  > - **RCM (Remote Center of Motion)** is a fundamental kinematic constraint for minimally invasive surgical robots. The surgical instrument passes through a fixed trocar port; the instrument must pivot about this pivot point without lateral sliding at the port, to avoid tissue injury.

> -There are two categories:

> -1. **Mechanical RCM**: A dedicated parallel or linkage mechanism physically enforces the pivot.
> -2. **Software RCM**: A general redundant manipulator (e.g., 7-DOF collaborative arm) uses constrained kinematics to satisfy the RCM rule in software. This is widely studied with ROS2.

> -ROS2 serves as the distributed software framework to integrate the whole robotic system. Compared with ROS1, its DDS-based communication, configurable QoS, real-time-friendly interfaces and modular `ros2_control` stack make it suitable for surgical robot research.
