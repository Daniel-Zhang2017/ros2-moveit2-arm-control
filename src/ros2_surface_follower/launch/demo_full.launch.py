from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node
import os

def generate_launch_description():
    pkg = FindPackageShare("ros2_surface_follower").find("ros2_surface_follower")
    world_path = PathJoinSubstitution([pkg, "worlds", "surface_wall.sdf"])
    urdf_path = PathJoinSubstitution([pkg, "urdf", "panda_end_cam.urdf.xacro"])
    surface_cfg = PathJoinSubstitution([pkg, "config", "surface_follower.yaml"])
    servo_cfg = PathJoinSubstitution([pkg, "config", "panda_servo.yaml"])
    rviz_cfg = PathJoinSubstitution([pkg, "config", "rviz_surface.rviz"])

    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    # 1. Gazebo
    gazebo_ros_share = FindPackageShare("gazebo_ros").find("gazebo_ros")
    gz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gazebo_ros_share, "launch", "gazebo.launch.py")),
        launch_arguments={"world": world_path, "use_sim_time": use_sim_time}.items(),
    )

    # 2. Robot State Publisher + Spawn Panda
    robot_state_pub = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{'robot_description': Command(['xacro ', urdf_path])}],
        output="screen"
    )
    spawn_robot = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=["-topic", "robot_description", "-entity", "panda"],
        output="screen"
    )

    # 3. depth_image_proc：depth image → pointcloud /camera/points
    depth2pc = Node(
        package="depth_image_proc",
        executable="point_cloud_xyz_node",
        name="depth2pc",
        remappings=[
            ("image_rect", "/camera/depth_image_raw"),
            ("camera_info", "/camera/camera_info"),
            ("points", "/camera/points"),
        ],
        output="screen"
    )

    # 4. Surface Follower node
    follower_node = Node(
        package="ros2_surface_follower",
        executable="surface_follower_node",
        name="surface_follower_node",
        parameters=[surface_cfg],
        output="screen"
    )

    # 5. MoveIt Servo
    servo_node = Node(
        package="moveit_servo",
        executable="servo_node_main",
        name="servo_node",
        parameters=[servo_cfg],
        output="screen"
    )

    # 6. RViz
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", rviz_cfg],
        output="screen"
    )

    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        gz_launch,
        robot_state_pub,
        spawn_robot,
        depth2pc,
        follower_node,
        servo_node,
        rviz
    ])
