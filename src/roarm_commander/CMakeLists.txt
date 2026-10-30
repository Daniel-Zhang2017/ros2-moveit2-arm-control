cmake_minimum_required(VERSION 3.8)
project(roarm_commander)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(moveit_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(example_interfaces REQUIRED)
find_package(my_robot_interfaces REQUIRED)

add_executable(commander src/commander.cpp)

ament_target_dependencies(
  commander
  rclcpp
  moveit_ros_planning_interface
  example_interfaces
  geometry_msgs
  moveit_msgs
  tf2
  my_robot_interfaces
)

install(
  TARGETS
    commander
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
