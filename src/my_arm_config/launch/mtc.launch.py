import os
from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    pkg_dir = get_package_share_directory("my_arm_config")
    kinematics_file = os.path.join(pkg_dir, "config", "kinematics.yaml")

    moveit_config = (
        MoveItConfigsBuilder("roarm_m3", package_name="my_arm_config")
        .robot_description_kinematics(kinematics_file)
        .to_moveit_configs()
    )

    mtc_node = Node(
        package="roarm_commander",
        executable="mtc_pick_place",
        name="mtc_pick_place_roarm_m3",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
        ]
    )

    return LaunchDescription([mtc_node])
