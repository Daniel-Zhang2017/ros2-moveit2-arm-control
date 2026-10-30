import os
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    pkg_dir = get_package_share_directory("my_arm_config")
    kinematics_file = os.path.join(pkg_dir, "config", "kinematics.yaml")

    moveit_config = (
        MoveItConfigsBuilder("roarm_m3", package_name="my_arm_config")
        .robot_description_kinematics(kinematics_file)
        .to_moveit_configs()
    )

    # move_group node + 强制OMPL参数
    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {
                "planning_pipelines": ["ompl"],
                "default_planning_pipeline": "ompl",
                "ompl.planning_plugin": "ompl_interface/OMPLPlanner"
            }
        ],
    )

    # RViz
    rviz_config_file = os.path.join(pkg_dir, "config", "moveit.rviz")
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", rviz_config_file],
        parameters=[moveit_config.to_dict()],
    )

    # 如果你原来demo需要fake ros2_control，这里加载robot launch
    # 取消下面注释，按需启用
    # robot_launch = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource([os.path.join(pkg_dir, "launch", "robot.launch.py")])
    # )
    # return LaunchDescription([robot_launch, move_group_node, rviz_node])

    return LaunchDescription([
        move_group_node,
        rviz_node
    ])
