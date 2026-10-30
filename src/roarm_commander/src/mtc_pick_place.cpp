#include <rclcpp/rclcpp.hpp>

#include <moveit/task_constructor/task.h>
#include <moveit/task_constructor/stages.h>
#include <moveit/task_constructor/solvers.h>

#include <moveit/planning_scene_interface/planning_scene_interface.h>
#include <moveit_msgs/msg/collision_object.hpp>
#include <shape_msgs/msg/solid_primitive.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

using namespace moveit::task_constructor;

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("mtc_pick_place_roarm_m3");

  Task task("roarm_m3_pick_place_task");
  try
  {
    task.loadRobotModel(node);
  }
  catch (const InitStageException& e)
  {
    RCLCPP_ERROR(node->get_logger(), "loadRobotModel failed: %s", e.what());
    rclcpp::shutdown();
    return 1;
  }

  // ✅ Use this solver variable everywhere
  auto solver = std::make_shared<solvers::PipelinePlanner>(node, "ompl");

  auto make_pose = [&](double x, double y, double z, double yaw)
  {
    geometry_msgs::msg::PoseStamped p;
    p.header.frame_id = "base_link";
    p.pose.position.x = x;
    p.pose.position.y = y;
    p.pose.position.z = z;
    tf2::Quaternion q;
    q.setRPY(0.0, 0.0, yaw);
    q.normalize();
    p.pose.orientation.x = q.getX();
    p.pose.orientation.y = q.getY();
    p.pose.orientation.z = q.getZ();
    p.pose.orientation.w = q.getW();
    return p;
  };

  // Add collision cube
  moveit::planning_interface::PlanningSceneInterface psi;
  shape_msgs::msg::SolidPrimitive cube;
  cube.type = shape_msgs::msg::SolidPrimitive::BOX;
  cube.dimensions = {0.04, 0.04, 0.04};

  geometry_msgs::msg::Pose cube_pose;
  cube_pose.position.x = 0.12;
  cube_pose.position.y = -0.10;
  cube_pose.position.z = 0.04;
  cube_pose.orientation.w = 1.0;

  moveit_msgs::msg::CollisionObject co;
  co.id = "pick_cube";
  co.header.frame_id = "base_link";
  co.primitives.push_back(cube);
  co.primitive_poses.push_back(cube_pose);
  co.operation = moveit_msgs::msg::CollisionObject::ADD;
  psi.applyCollisionObjects({co});

  task.add(std::make_unique<stages::CurrentState>("current_state"));

  // Pre-grasp
  {
    auto pre_grasp_pose = make_pose(0.12, -0.10, 0.10, 0.0);
    auto move_pregrasp = std::make_unique<stages::MoveTo>("move_pregrasp", solver);
    move_pregrasp->setGroup("hand");
    move_pregrasp->setGoal(pre_grasp_pose);
    task.add(std::move(move_pregrasp));
  }

  // Grasp with ComputeIK
  {
    auto grasp_pose = make_pose(0.12, -0.10, 0.06, 0.0);
    auto move_to_grasp = std::make_unique<stages::MoveTo>("move_to_grasp", solver);
    move_to_grasp->setGroup("hand");
    move_to_grasp->setGoal(grasp_pose);

    auto ik_grasp = std::make_unique<stages::ComputeIK>("ik_grasp", std::move(move_to_grasp));
    ik_grasp->setIKFrame("gripper_link");
    ik_grasp->setTimeout(0.2);
    task.add(std::move(ik_grasp));
  }

  // Close gripper
  {
    auto close_gripper = std::make_unique<stages::MoveTo>("close_gripper", solver);
    close_gripper->setGroup("hand_gripper");
    close_gripper->setGoal("close");
    task.add(std::move(close_gripper));
  }

  // Attach cube
  {
    auto attach_cube = std::make_unique<stages::ModifyPlanningScene>("attach_cube");
    attach_cube->attachObject("pick_cube", "gripper_link");
    task.add(std::move(attach_cube));
  }

  // Lift
  {
    auto lift_pose = make_pose(0.12, -0.10, 0.15, 0.0);
    auto move_lift = std::make_unique<stages::MoveTo>("move_lift", solver);
    move_lift->setGroup("hand");
    move_lift->setGoal(lift_pose);
    task.add(std::move(move_lift));
  }

  // Move to place
  {
    auto place_pose = make_pose(0.10, 0.10, 0.10, 0.0);
    auto move_place = std::make_unique<stages::MoveTo>("move_place", solver);
    move_place->setGroup("hand");
    move_place->setGoal(place_pose);
    task.add(std::move(move_place));
  }

  // Detach cube
  {
    auto detach_cube = std::make_unique<stages::ModifyPlanningScene>("detach_cube");
    detach_cube->detachObject("pick_cube", "gripper_link");
    task.add(std::move(detach_cube));
  }

  // Open gripper
  {
    auto open_gripper = std::make_unique<stages::MoveTo>("open_gripper", solver);
    open_gripper->setGroup("hand_gripper");
    open_gripper->setGoal("open");
    task.add(std::move(open_gripper));
  }

  task.init();
  moveit::core::MoveItErrorCode plan_result = task.plan();
  if (plan_result.val != moveit_msgs::msg::MoveItErrorCodes::SUCCESS)
  {
    RCLCPP_ERROR(node->get_logger(), "❌ MTC Plan FAILED");
    psi.removeCollisionObjects({"pick_cube"});
    rclcpp::shutdown();
    return 1;
  }

  RCLCPP_INFO(node->get_logger(), "✅ MTC Pick&Place PLAN SUCCESS!");
  const auto& solutions = task.solutions();
  if (!solutions.empty())
  {
    auto sol_it = solutions.begin();
    moveit::core::MoveItErrorCode exec_result = task.execute(**sol_it);
    if (exec_result.val == moveit_msgs::msg::MoveItErrorCodes::SUCCESS)
    {
      RCLCPP_INFO(node->get_logger(), "✅ Execution completed!");
    }
    else
    {
      RCLCPP_ERROR(node->get_logger(), "❌ Execution failed!");
    }
  }

  psi.removeCollisionObjects({"pick_cube"});
  rclcpp::shutdown();
  return 0;
}
