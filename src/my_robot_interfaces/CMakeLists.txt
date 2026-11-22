cmake_minimum_required(VERSION 3.8)
project(my_robot_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(action_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/PoseCommand.msg"
  "action/ArmCommand.action"
  DEPENDENCIES
    builtin_interfaces
    std_msgs
    geometry_msgs
    action_msgs
)

# 拿到 cpp typesupport 目标，并且导出
rosidl_get_typesupport_target(cpp_typesupport_target "${PROJECT_NAME}" "rosidl_typesupport_cpp")
ament_export_targets(${cpp_typesupport_target})

ament_export_dependencies(rosidl_default_runtime)
ament_package()
