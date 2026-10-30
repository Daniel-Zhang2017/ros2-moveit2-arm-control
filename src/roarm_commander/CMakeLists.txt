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
find_package(moveit_task_constructor_core REQUIRED)
find_package(moveit_task_constructor_msgs REQUIRED)  # ✅ ADD THIS

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

add_executable(mtc_pick_place src/mtc_pick_place.cpp)

ament_target_dependencies(mtc_pick_place
  rclcpp
  moveit_ros_planning_interface
  tf2
  tf2_geometry_msgs
  my_robot_interfaces
  moveit_task_constructor_msgs   # ✅ ADD THIS
)

# ✅ Direct absolute .so link for MTC core (keep this, it fixed ld error)
set(MTC_LIB_DIR "/home/da/roarm_ws/install/moveit_task_constructor_core/lib")
target_link_libraries(mtc_pick_place
  ${MTC_LIB_DIR}/libmoveit_task_constructor_core.so
  ${MTC_LIB_DIR}/libmoveit_task_constructor_core_stages.so
  ${MTC_LIB_DIR}/libmoveit_task_constructor_core_stage_plugins.so
)

# ✅ MTC core header include
target_include_directories(mtc_pick_place PRIVATE
  /home/da/roarm_ws/install/moveit_task_constructor_core/include
)

install(
  TARGETS
    commander
    mtc_pick_place
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
