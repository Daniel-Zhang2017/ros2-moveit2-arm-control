from launch import LaunchDescription
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.substitutions import PathJoinSubstitution

from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch


def generate_launch_description():
    # 1. Build moveit config (single source of robot description / srdf / kinematics)
    moveit_config = (
        MoveItConfigsBuilder("my_robot", package_name="my_moveit_config")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .to_moveit_configs()
    )

    # 2. Paths
    bringup_share = FindPackageShare("my_robot_bringup")
    controller_yaml = PathJoinSubstitution([bringup_share, "config", "ros2_controllers.yaml"])
    rviz_config = PathJoinSubstitution([bringup_share, "config", "my_moveit.rviz"])

    # 3. robot_state_publisher: use moveit_config's robot_description
    rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[moveit_config.robot_description],
    )

    # 4. ros2_control_node
    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        output="screen",
        parameters=[
            moveit_config.robot_description,
            controller_yaml,
        ],
    )

    # 5. Spawn controllers with --wait-for-controller-manager
    spawn_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--wait-for-controller-manager"],
        output="screen",
    )
    spawn_arm = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["arm_controller", "--wait-for-controller-manager"],
        output="screen",
    )
    spawn_gripper = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["gripper_controller", "--wait-for-controller-manager"],
        output="screen",
    )

    # 6. move_group
    move_group_ld = generate_move_group_launch(moveit_config)

    # 7. RViz2
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", rviz_config],
        output="screen",
    )

    return LaunchDescription([
        rsp,
        control_node,
        spawn_broadcaster,
        spawn_arm,
        spawn_gripper,
        *move_group_ld.entities,
        rviz,
    ])
