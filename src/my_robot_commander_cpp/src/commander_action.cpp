#include <rclcpp/rclcpp.hpp>
#include <rclcpp_action/rclcpp_action.hpp>

#include <moveit/move_group_interface/move_group_interface.h>
#include <moveit_msgs/msg/move_it_error_codes.hpp>
#include <moveit_msgs/msg/robot_trajectory.hpp>

#include <my_robot_interfaces/action/arm_command.hpp>
#include <tf2/LinearMath/Quaternion.h>

#include <memory>
#include <string>
#include <thread>

using ArmCommand = my_robot_interfaces::action::ArmCommand;
using GoalHandleArm = rclcpp_action::ServerGoalHandle<ArmCommand>;
using MoveGroupInterface = moveit::planning_interface::MoveGroupInterface;

class ArmCommanderNode : public rclcpp::Node
{
public:
    ArmCommanderNode() : Node("arm_commander_action")
    {
    }

    void init(std::shared_ptr<ArmCommanderNode> self)
    {
        arm_ = std::make_shared<MoveGroupInterface>(self, "arm");
        gripper_ = std::make_shared<MoveGroupInterface>(self, "gripper");
        arm_->setMaxVelocityScalingFactor(1.0);
        arm_->setMaxAccelerationScalingFactor(1.0);

        action_server_ = rclcpp_action::create_server<ArmCommand>(
            self,
            "arm_command",
            std::bind(&ArmCommanderNode::handle_goal, this, std::placeholders::_1, std::placeholders::_2),
            std::bind(&ArmCommanderNode::handle_cancel, this, std::placeholders::_1),
            std::bind(&ArmCommanderNode::handle_accepted, this, std::placeholders::_1));

        RCLCPP_INFO(get_logger(), "Arm Action Server ready");
    }

private:
    rclcpp_action::GoalResponse handle_goal(
        const rclcpp_action::GoalUUID &,
        [[maybe_unused]] std::shared_ptr<const ArmCommand::Goal> goal)
    {
        if (current_goal_handle_)
        {
            RCLCPP_WARN(get_logger(), "Busy, rejecting new goal");
            return rclcpp_action::GoalResponse::REJECT;
        }
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
    }

    rclcpp_action::CancelResponse handle_cancel(
        [[maybe_unused]] const std::shared_ptr<GoalHandleArm> goal_handle)
    {
        RCLCPP_INFO(get_logger(), "Cancel requested");
        if (arm_) arm_->stop();
        if (gripper_) gripper_->stop();
        return rclcpp_action::CancelResponse::ACCEPT;
    }

    void handle_accepted(const std::shared_ptr<GoalHandleArm> goal_handle)
    {
        current_goal_handle_ = goal_handle;
        std::thread{
            std::bind(&ArmCommanderNode::execute_goal, this, goal_handle)
        }.detach();
    }

    void execute_goal(const std::shared_ptr<GoalHandleArm> goal_handle)
    {
        const auto goal = goal_handle->get_goal();
        auto feedback = std::make_shared<ArmCommand::Feedback>();
        auto result = std::make_shared<ArmCommand::Result>();

        bool ok = true;
        std::string err_msg;

        feedback->success = true;
        feedback->message = "start planning";
        goal_handle->publish_feedback(feedback);

        try
        {
            if (goal->command_type == 1)
            {
                goToJointTarget(goal->joint_target);
            }
            else if (goal->command_type == 2)
            {
                goToPoseTarget(
                    goal->x, goal->y, goal->z,
                    goal->roll, goal->pitch, goal->yaw,
                    goal->cartesian_path);
            }
            else if (goal->command_type == 3)
            {
                goToNamedTarget(goal->named_target);
            }
            else if (goal->command_type == 4)
            {
                if (goal->gripper_open)
                    openGripper();
                else
                    closeGripper();
            }
            else
            {
                throw std::runtime_error("unknown command_type");
            }

            feedback->success = true;
            feedback->message = "execution finished";
            goal_handle->publish_feedback(feedback);

            result->progress = 1.0;
            result->status_msg = "success";
        }
        catch (const std::exception &e)
        {
            ok = false;
            err_msg = e.what();
            result->progress = 0.0;
            result->status_msg = "error: " + err_msg;
        }

        if (goal_handle->is_canceling())
        {
            result->progress = 0.0;
            result->status_msg = "canceled";
            goal_handle->canceled(result);
        }
        else if (ok)
        {
            goal_handle->succeed(result);
        }
        else
        {
            goal_handle->abort(result);
        }

        current_goal_handle_.reset();
    }

    void goToNamedTarget(const std::string &name)
    {
        arm_->setNamedTarget(name);
        planAndExecute(arm_);
    }

    void goToJointTarget(const std::vector<double> &joints)
    {
        arm_->setJointValueTarget(joints);
        planAndExecute(arm_);
    }

    void goToPoseTarget(
        double x, double y, double z,
        double roll, double pitch, double yaw,
        bool cartesian_path)
    {
        tf2::Quaternion q;
        q.setRPY(roll, pitch, yaw);

        geometry_msgs::msg::PoseStamped target;
        target.header.frame_id = arm_->getPlanningFrame();
        target.pose.position.x = x;
        target.pose.position.y = y;
        target.pose.position.z = z;
        target.pose.orientation.x = q.x();
        target.pose.orientation.y = q.y();
        target.pose.orientation.z = q.z();
        target.pose.orientation.w = q.w();

        if (cartesian_path)
        {
            std::vector<geometry_msgs::msg::Pose> waypoints;
            waypoints.push_back(target.pose);
            moveit_msgs::msg::RobotTrajectory traj;
            double fraction = arm_->computeCartesianPath(waypoints, 0.01, 0.0, traj, true);
            if (fraction < 0.999)
                throw std::runtime_error("cartesian path incomplete");
            arm_->execute(traj);
        }
        else
        {
            arm_->setPoseTarget(target);
            planAndExecute(arm_);
        }
    }

    void openGripper()
    {
        gripper_->setNamedTarget("gripper_open");
        planAndExecute(gripper_);
    }

    void closeGripper()
    {
        gripper_->setNamedTarget("gripper_closed");
        planAndExecute(gripper_);
    }

    void planAndExecute(std::shared_ptr<MoveGroupInterface> &mg)
    {
        moveit::planning_interface::MoveGroupInterface::Plan plan;
        auto plan_result = mg->plan(plan);
        if (!plan_result)
        {
            throw std::runtime_error("plan failed");
        }
        mg->execute(plan);
    }

    std::shared_ptr<MoveGroupInterface> arm_;
    std::shared_ptr<MoveGroupInterface> gripper_;
    rclcpp_action::Server<ArmCommand>::SharedPtr action_server_;
    std::shared_ptr<GoalHandleArm> current_goal_handle_;
};

int main(int argc, char ** argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<ArmCommanderNode>();
    node->init(node);
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
