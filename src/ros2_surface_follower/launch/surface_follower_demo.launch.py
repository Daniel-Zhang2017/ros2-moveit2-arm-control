from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    pkg = FindPackageShare("ros2_surface_follower").find("ros2_surface_follower")
    cfg = PathJoinSubstitution([pkg, "config", "surface_follower.yaml"])

    follower_node = Node(
        package="ros2_surface_follower",
        executable="surface_follower_node",
        name="surface_follower_node",
        parameters=[cfg],
        output="screen"
    )

    return LaunchDescription([follower_node])
