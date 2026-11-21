from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch


def generate_launch_description():
    moveit_config = (
        MoveItConfigsBuilder("my_robot", package_name="my_moveit_config")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .planning_pipelines(
            pipelines=["ompl", "pilz_industrial_motion_planner"],
            default_planning_pipeline="ompl"
        )
        .to_moveit_configs()
    )
    return generate_move_group_launch(moveit_config)
