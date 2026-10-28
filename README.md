# 6-DoF Robotic Arm ROS 2 + MoveIt 2 Stack
A complete ROS 2 Humble workspace for a **6-joint manipulator with a parallel gripper**, including robot description, MoveIt 2 planning config, hardware bringup, **custom C++ motion commander**, MoveIt2 MTC (MoveIt Task Constructor), and custom ROS 2 interfaces.

>In an actual robotic arm system, other ROS 2 nodes can send joint targets, end-effector poses, or grasping tasks to the **Commander node via topics, services, or actions**. 

>The **Commander node** calls MoveIt 2 through the MoveIt API to perform kinematics computation, collision detection, and trajectory planning. The resulting joint trajectory is then sent through the MoveIt controller to the trajectory controller in ros2_control, which further converts it into control commands for the real robotic arm or simulated hardware. During hardware execution, state information such as joint positions and velocities is continuously returned; ros2_control publishes these states as joint states, and robot_state_publisher then publishes TF coordinate transforms in combination with the URDF model, allowing MoveIt and RViz to obtain the current robot pose.

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
*Video 1: Arm motion demo, recorded at 100 Hz joint states: ros2 bag record /joint_states*

https://github.com/user-attachments/assets/a827dda0-dc04-47a8-88f3-8c268dc0bbe3

*Video 2: Roarm control and motion: Cartesian path*

https://github.com/user-attachments/assets/c8ac123a-d9f0-467d-afe4-b9e7536e7b07

*Video 3: Real arm Cartesian path*

https://github.com/user-attachments/assets/b6f72d57-6e1e-4b73-a8a3-074690e890e5

*Video 4: Real robotic arm control and motion*

https://github.com/user-attachments/assets/7caf02ca-e448-450b-a686-7556f6876fa5

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
│       ├── test_moveit.cpp
│       └── test2_moveit.cpp
├── my_robot_description      # Robot URDF / Xacro model
│   ├── urdf/                 # Arm, gripper, common properties, ros2_control xacro
│   └── launch/display.launch.xml  # Quick URDF visualization only
├── my_robot_interfaces       # Custom ROS 2 message definitions
│   └── msg/PoseCommand.msg   # Custom pose command with RPY + Cartesian flag
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

>**Capture the RViz window into `raw_capture.mp4`**

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
# Notes: 

1. The core difference between Python and XML launch files in ROS 2 lies in flexibility versus declarative simplicity. Python offers powerful programming capabilities and lower-level access, making it suitable for complex logic; XML is more concise and declarative, making it suitable for simple, straightforward startup tasks and users migrating from ROS 1.


> 2. MoveIt 2 is a widely used motion planning framework in ROS 2. It is responsible for generating motion trajectories based on robot models, joint limits, collision information, and target states, though it does not directly control the motors.

### 3. Configure a robotic arm visually using the MoveIt Setup Assistant

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

## 4. Comparison: PTP Joint Planning vs Cartesian Planning

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

# 6. Real robotic arm control and motion

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

## 7. MTC solves complex manipulation tasks by splitting the job into composable `Stage`s. Instead of one-shot motion planning, MTC explores alternative solution branches, backtracks on failure, and manages `PlanningScene` states (attach/detach objects) automatically.

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

## Related Projects

- [roarm_ws](https://github.com/Daniel-Zhang2017/roarm_ws) — real arm control and motion

- [ros2-robotics-projects](https://github.com/Daniel-Zhang2017/ros2-robotics-projects) — autonomous mobile robots and robotic arms
