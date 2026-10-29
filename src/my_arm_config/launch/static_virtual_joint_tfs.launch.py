from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_static_virtual_joint_tfs_launch


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder("roarm_m3", package_name="my_arm_config").to_moveit_configs()
    return generate_static_virtual_joint_tfs_launch(moveit_config)
