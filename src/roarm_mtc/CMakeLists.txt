cmake_minimum_required(VERSION 3.8)
project(roarm_mtc)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(moveit_ros_planning REQUIRED)
find_package(moveit_task_constructor_core REQUIRED)
find_package(moveit_task_constructor_msgs REQUIRED)
find_package(ament_index_cpp REQUIRED)

# --- 关键：执行ros2 pkg prefix命令拿到路径
execute_process(
  COMMAND ros2 pkg prefix moveit_task_constructor_core
  OUTPUT_VARIABLE MTC_CORE_PREFIX
  OUTPUT_STRIP_TRAILING_WHITESPACE
)
set(MTC_LIB_DIR "${MTC_CORE_PREFIX}/lib")

message(STATUS "MTC core prefix: ${MTC_CORE_PREFIX}")
message(STATUS "MTC lib dir: ${MTC_LIB_DIR}")

add_executable(mtc_pick_place src/mtc_pick_place.cpp)

ament_target_dependencies(mtc_pick_place
  rclcpp
  moveit_ros_planning
  moveit_task_constructor_core
  moveit_task_constructor_msgs
  ament_index_cpp
)

# 链接顺序：solvers → stages → core（依赖顺序不能反）
target_link_libraries(mtc_pick_place
  ${MTC_LIB_DIR}/libmoveit_task_constructor_solvers.so
  ${MTC_LIB_DIR}/libmoveit_task_constructor_stages.so
  ${MTC_LIB_DIR}/libmoveit_task_constructor_core.so
)

install(TARGETS
  mtc_pick_place
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
