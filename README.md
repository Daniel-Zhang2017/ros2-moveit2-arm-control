# ros2-moveit2-arm-control

ros2-moveit2-arm-control



```

\#installation dependencies

sudo apt update

sudo apt install ros-humble-moveit ros-humble-moveit-ros-planning-interface

source /opt/ros/humble/setup.bash

source install/setup.bash



colcon build

source install/setup.bash

ros2 launch my\_robot\_description display.launch.xml 



\#The core difference between Python and XML launch files in ROS 2 lies in flexibility versus declarative simplicity. Python offers powerful #programming capabilities and lower-level access, making it suitable for complex logic; XML is more concise and declarative, making it suitable #for simple, straightforward startup tasks and users migrating from ROS 1 .



```

\## Overview

>MoveIt 2 is a widely used motion planning framework in ROS 2. It is responsible for generating motion trajectories based on robot models, joint limits, collision information, and target states, though it does not directly control the motors.



\### Configure a robotic arm visually using the MoveIt Setup Assistant



MoveIt Setup Assistant (MSA) — Description

> 

> \*\*MoveIt Setup Assistant\*\* is the official GUI wizard tool for MoveIt 2 (ROS 2 Humble/Iron/Jazzy), used to \*\*generate all required MoveIt configuration packages from your robot URDF/Xacro\*\*. It automates the tedious YAML / SRDF / controller config creation, so you can quickly get your manipulator ready for planning, RViz demo, ros2\_control and execution.



>A planning group defines a collection of joints and links that MoveIt will treat as a single controllable kinematic subsystem, such as a robotic arm or gripper. Each planning group is assigned an inverse kinematics solver, search parameters and a default motion planner.



>\*\*Inverse Kinematics (IK)\*\* solves the problem:



> 

> Given a desired end-effector Cartesian pose (position + orientation in 3D space), calculate the corresponding set of joint angles for your robot arm.



>Forward kinematics does the opposite: input joint angles → compute end-effector pose.



```

ros2 launch moveit\_setup\_assistant setup\_assistant.launch.py 

```

```

colcon build --packages-select my\_moveit\_config

source install/setup.bash



ros2 launch my\_moveit\_config demo.launch.py

```

In the RViz2 Motion Planning panel:

>1. Set goal (drag interactive marker or joint slider), or adjust Start State, Goal State under the Planning/Query

>2. Click \*\*Plan\*\* → preview path drawn, robot stays still

>3. Then click \*\*Execute\*\* → robot moves Or directly click \*\*Plan \& Execute\*\* to combine two steps

>4. Rviz motionplaning/scene objects panel: The Scene Objects panel in the MoveIt RViz Motion Planning plugin is where you manage the collision environment. You use it to add, move, attach, or remove objects that the robot must avoid during motion planning.







\## Overview

`MoveGroupInterface` is the \*\*core C++ API class\*\* in MoveIt2 (header: `moveit/move\_group\_interface/move\_group\_interface.h`).

It acts as a high-level wrapper to communicate with the `move\_group` node.

You use it to command a robot planning group: set target pose / joint goal, run motion planning, execute trajectory, query robot state, perform Cartesian path planning, etc.



> ✅ In short:

> \*\*MoveGroupInterface = the main C++ bridge between your user program and the MoveIt move\_group server.\*\*

> It hides the low-level ROS service / action calls, so you do not manually send action goals.



\## Comparison: PTP Joint Planning vs Cartesian Planning



| Feature | PTP Joint Space Planning | Cartesian Path Planning |

|---|---|---|

| Trajectory control | Only start \& goal joint states | End-effector TCP path |

| End-effector path | Curved, uncontrolled | Near straight line |

| Computation cost | Low | High (IK at every sample) |

| Singularity risk | Low | High |

| Use cases | Pick \& place, point reaching | Welding, grinding, dispensing, assembly |



\## Safety Warning

Do NOT set `jump\_threshold = 0` on a real robot.



Cartesian IK may switch to a different joint solution and cause sudden, unsafe large joint motion.

Always perform full simulation validation and enable collision checking before real robot operation.

```

source install/setup.bash

ros2 launch my\_robot\_bringup my\_robot.launch.xml

```

```

source install/setup.bash

ros2 run my\_robot\_commander\_cpp test\_moveit

```



```

ros2 launch my\_robot\_commander\_cpp test2\_moveit

```



```

ros2 launch my\_robot\_commander\_cpp commander\_template

```

\# my\_robot\_commander\_cpp

A lightweight \*\*MoveIt2 C++ motion commander node\*\* for a 6DoF robotic arm + gripper, built for ROS 2 Humble / Iron.

It wraps `MoveGroupInterface`, supports joint target, pose target (normal / Cartesian straight line), named SRDF poses, and gripper control via ROS 2 topics.



> This package works together with:

> - `my\_moveit\_config` (MoveIt planning config, SRDF, kinematics yaml)

> - `my\_robot\_description` (URDF/Xacro robot model)

> - `my\_robot\_bringup` (launch file to bringup robot\_state\_publisher, ros2\_control, move\_group, RViz)

> - `my\_robot\_interfaces` (custom `PoseCommand` message)



\## Features

\- ✅ Named target motion (`home`, `pose\_1`, gripper `gripper\_open` / `gripper\_closed`)

\- ✅ Joint-space target control (6 joint values)

\- ✅ Pose target control (X,Y,Z + RPY Euler angle)

&#x20; - Normal MoveIt planning (collision-aware, non-straight)

&#x20; - Cartesian straight-line planning (`computeCartesianPath`)

\- ✅ Gripper open / close control

\- ✅ Topic-based runtime command interface

\- ✅ Multi-threaded executor: motion execution and topic callbacks run concurrently

\- ✅ Built-in logging and simple planning/execution error checking



\## ROS 2 Topics

\### Subscribed Topics

| Topic name | Message Type | Description |

|---|---|---|

| `/open\_gripper` | `example\_interfaces/msg/Bool` | `true` = open gripper; `false` = close gripper |

| `/joint\_command` | `example\_interfaces/msg/Float64MultiArray` | 6 joint angles for the arm |

| `/pose\_command` | `my\_robot\_interfaces/msg/PoseCommand` | End-effector pose target + cartesian flag |



> Definition of `PoseCommand` (my\_robot\_interfaces):

> ```

> float64 x

> float64 y

> float64 z

> float64 roll

> float64 pitch

> float64 yaw

> bool cartesian\_path

> ```

> `cartesian\_path=true`: try straight-line Cartesian motion; `false`: normal pose planning.



\## Dependencies

Add these to your `package.xml`:

```xml

<buildtool\_depend>ament\_cmake</buildtool\_depend>



<depend>rclcpp</depend>

<depend>moveit\_ros\_move\_group</depend>

<depend>moveit\_core</depend>

<depend>tf2\_geometry\_msgs</depend>

<depend>example\_interfaces</depend>

<depend>my\_robot\_interfaces</depend>



\## Send Command via CLI (after commander is running)



```

\# Open gripper

ros2 topic pub /open\_gripper example\_interfaces/msg/Bool "{data: true}"



\# Close gripper

ros2 topic pub /open\_gripper example\_interfaces/msg/Bool "{data: false}"



\# Send joint command (6 joints)

ros2 topic pub /joint\_command example\_interfaces/msg/Float64MultiArray "{data: \[0, -0.785, 1.57, -0.785, 0, 0]}"

```





