# 6-DoF Robotic Arm ROS 2 + MoveIt 2 Stack
A complete ROS 2 Humble workspace for a 6-joint manipulator with parallel gripper, including robot description, MoveIt 2 planning config, hardware bringup, **custom C++ motion commander** and custom ROS 2 interfaces.
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
## Project Structure
```
## Repository Structure

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
│       ├── test_moveit.cpp
│       └── test2_moveit.cpp
├── my_robot_description      # Robot URDF / Xacro model
│   ├── urdf/                 # Arm, gripper, common properties, ros2_control xacro
│   └── launch/display.launch.xml  # Quick URDF visualization only
├── my_robot_interfaces       # Custom ROS 2 message definitions
│   └── msg/PoseCommand.msg   # Custom pose command with RPY + Cartesian flag


## System Overview
This stack implements a standard `ros2_control` + MoveIt 2 pipeline:
1. `my_robot_description`: Kinematic model of 6DoF arm + gripper, with ros2_control transmission tags
2. `my_moveit_config`: MoveIt setup: semantic SRDF, KDL kinematics solver, joint limits, OMPL planner
3. `my_robot_bringup`: Single XML launch file to start the whole control stack
4. `my_robot_commander_cpp`: High-level C++ commander node that wraps `MoveGroupInterface`
   - Supports named SRDF poses, joint targets, pose targets (normal planning / Cartesian straight line)
   - Topic-based runtime control for arm and gripper
5. `my_robot_interfaces`: Custom `PoseCommand` message for end-effector pose goals

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

C++ commander node (`commander_template.cpp`):

- Two MoveGroup instances: `"arm"` and `"gripper"`
- Subscribers:
  - `/open_gripper` (`example_interfaces/msg/Bool`): `true` open, `false` close
  - `/joint_command` (`example_interfaces/msg/Float64MultiArray`): 6 joint angles for arm
  - `/pose_command` (`my_robot_interfaces/msg/PoseCommand`): `x,y,z,roll,pitch,yaw,cartesian_path`
- API:
  - `goToNamedTarget(name)`: move arm to SRDF named pose
  - `goToJointTarget(joints)`: joint-space target
  - `goToPoseTarget(x,y,z,r,p,y, cartesian_path)`: pose target
    - `cartesian_path=false`: normal MoveIt collision-aware planning
    - `cartesian_path=true`: local `computeCartesianPath` straight line
  - `openGripper()` / `closeGripper()`: gripper named states

> 
> ⚠️ Important limitation: `computeCartesianPath` runs locally inside this commander node. You need to load `kinematics.yaml` as node parameters into the commander to avoid `No kinematics plugins defined` warning and 0% cartesian fraction. Normal pose planning sends goals to `/move_group` and uses the move_group process’s kinematics settings.

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

## Build Instructions

Build all packages in your ROS 2 workspace:
```
colcon build --packages-select my_robot_description my_moveit_config my_robot_bringup my_robot_interfaces my_robot_commander_cpp
source install/setup.bash
```

## Runtime Sequence

1. Terminal 1 — launch full robot + MoveIt stack

```
ros2 launch my_robot_bringup my_robot.launch.xml
```

2. Terminal 2 — run C++ motion commander

```
ros2 run my_robot_commander_cpp commander_template
```

> 
> The built-in demo sequence inside `main()` will run automatically once commander starts:
> Move → close gripper → lift → return home → open gripper, then listen for topic commands.

### Send runtime commands via CLI

```
# Open gripper
ros2 topic pub /open_gripper example_interfaces/msg/Bool "{data: true}"

# Close gripper
ros2 topic pub /open_gripper example_interfaces/msg/Bool "{data: false}"

# Send 6 joint target (radians)
ros2 topic pub /joint_command example_interfaces/msg/Float64MultiArray "{data: [0, -0.785, 1.57, -0.785, 0, 0]}"
```

#Notes: 

The core difference between Python and XML launch files in ROS 2 lies in flexibility versus declarative simplicity. Python offers powerful programming capabilities and lower-level access, making it suitable for complex logic; XML is more concise and declarative, making it suitable for simple, straightforward startup tasks and users migrating from ROS 1.


> MoveIt 2 is a widely used motion planning framework in ROS 2. It is responsible for generating motion trajectories based on robot models, joint limits, collision information, and target states, though it does not directly control the motors.

### Configure a robotic arm visually using the MoveIt Setup Assistant

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

Comparison: PTP Joint Planning vs Cartesian Planning
Feature	PTP Joint Space Planning	Cartesian Path Planning
Trajectory control	Only start & goal joint states	End-effector TCP path
End-effector path	Curved, uncontrolled	Near straight line
Computation cost	Low	High (IK at every sample)
Singularity risk	Low	High
Use cases	Pick & place, point reaching	Welding, grinding, dispensing, assembly
**Safety Warning**

>Do NOT set jump_threshold = 0 on a real robot.

>Cartesian IK may switch to a different joint solution and cause sudden, unsafe large joint motion.

>Always perform full simulation validation and enable collision checking before real robot operation.

