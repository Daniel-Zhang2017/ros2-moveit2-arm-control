from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_move_group_launch


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder("roarm_m3", package_name="my_arm_config").to_moveit_configs()

    # ✅ Correct attribute: move_group_params
    moveit_config.move_group_params.update({
        "planning_pipelines": ["ompl"],
        "default_planning_pipeline": "ompl",
        "ompl.planning_plugin": "ompl_interface/OMPLPlanner"
    })

    return generate_move_group_launch(moveit_config)
