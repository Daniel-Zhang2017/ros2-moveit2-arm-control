#include <rclcpp/rclcpp.hpp>

#include <moveit/move_group_interface/move_group_interface.h>
#include <moveit/robot_model/robot_model.h>
#include <moveit/robot_model_loader/robot_model_loader.h>

#include <sensor_msgs/msg/joint_state.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <moveit_msgs/msg/move_it_error_codes.hpp>
#include <moveit_msgs/msg/robot_trajectory.hpp>

#include <tf2/LinearMath/Quaternion.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

#include <chrono>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

using MoveGroupInterface = moveit::planning_interface::MoveGroupInterface;

class Commander
{
public:
    Commander(const std::shared_ptr<rclcpp::Node>& node)
        : node_(node), received_joint_state_(false)
    {
        arm_ = std::make_shared<MoveGroupInterface>(node_, "hand");
        gripper_ = std::make_shared<MoveGroupInterface>(node_, "gripper");

        // The order must match the order published in /joint_states
        expected_joint_names_ = {
            "base_link_to_link1",
            "link2_to_link3",
            "link1_to_link2",
            "link3_to_link4",
            "link4_to_link5",
            "link5_to_gripper_link"
        };

        joint_state_sub_ = node_->create_subscription<sensor_msgs::msg::JointState>(
            "/joint_states",
            10,
            std::bind(&Commander::jointStateCallback, this, std::placeholders::_1));
    }

    void jointStateCallback(const sensor_msgs::msg::JointState::SharedPtr msg)
    {
        std::lock_guard<std::mutex> lock(mtx_);

        std::vector<double> positions(expected_joint_names_.size(), 0.0);
        bool found_all = true;

        for (size_t i = 0; i < expected_joint_names_.size(); ++i)
        {
            auto it = std::find(msg->name.begin(), msg->name.end(), expected_joint_names_[i]);
            if (it == msg->name.end())
            {
                found_all = false;
                break;
            }
            size_t idx = std::distance(msg->name.begin(), it);
            positions[i] = msg->position[idx];
        }

        if (found_all)
        {
            latest_joint_positions_ = positions;
            received_joint_state_ = true;
        }
    }

    bool setStartStateFromLatestJoints()
    {
        std::lock_guard<std::mutex> lock(mtx_);
        if (!received_joint_state_)
        {
            RCLCPP_WARN(node_->get_logger(), "No valid joint state received yet.");
            return false;
        }

        auto state = arm_->getCurrentState();
        const auto* jmg = arm_->getRobotModel()->getJointModelGroup(arm_->getName());
        state->setJointGroupPositions(jmg, latest_joint_positions_);
        arm_->setStartState(*state);
        return true;
    }

    void goToNamedTarget(const std::string& name)
    {
        if (!setStartStateFromLatestJoints())
            return;
        arm_->setNamedTarget(name);
        planAndExecute(arm_);
    }

    void goToJointTarget(const std::vector<double>& joints)
    {
        if (joints.size() != expected_joint_names_.size())
        {
            RCLCPP_ERROR(node_->get_logger(), "Joint count mismatch.");
            return;
        }
        if (!setStartStateFromLatestJoints())
            return;
        arm_->setJointValueTarget(joints);
        planAndExecute(arm_);
    }

    void goToPoseTarget(
        double x, double y, double z,
        double roll, double pitch, double yaw,
        bool cartesian_path = false)
    {
        if (!setStartStateFromLatestJoints())
            return;

        tf2::Quaternion q;
        q.setRPY(roll, pitch, yaw);
        q.normalize();

        geometry_msgs::msg::PoseStamped target_pose;
        target_pose.header.frame_id = arm_->getPlanningFrame();
        target_pose.pose.position.x = x;
        target_pose.pose.position.y = y;
        target_pose.pose.position.z = z;
        target_pose.pose.orientation = tf2::toMsg(q);

        if (!cartesian_path)
        {
            arm_->setPoseTarget(target_pose);
            planAndExecute(arm_);
            arm_->clearPoseTargets();
        }
        else
        {
            std::vector<geometry_msgs::msg::Pose> waypoints;
            waypoints.push_back(target_pose.pose);
            moveit_msgs::msg::RobotTrajectory trajectory;
            double fraction = arm_->computeCartesianPath(waypoints, 0.01, 0.1, trajectory);
            if (fraction >= 0.99)
            {
                arm_->execute(trajectory);
            }
            else
            {
                RCLCPP_WARN(node_->get_logger(), "Cartesian path incomplete: %.2f", fraction);
            }
        }
    }

    void openGripper()
    {
        gripper_->setNamedTarget("open");
        planAndExecute(gripper_);
    }

    void closeGripper()
    {
        gripper_->setNamedTarget("close");
        planAndExecute(gripper_);
    }

private:
    void planAndExecute(const std::shared_ptr<MoveGroupInterface>& group)
    {
        MoveGroupInterface::Plan plan;
        auto ok = group->plan(plan);
        if (ok != moveit::planning_interface::MoveItErrorCode::SUCCESS)
        {
            RCLCPP_ERROR(node_->get_logger(), "Planning failed.");
            return;
        }
        auto exec_result = group->execute(plan);
        if (exec_result != moveit::planning_interface::MoveItErrorCode::SUCCESS)
        {
            RCLCPP_ERROR(node_->get_logger(), "Execution failed.");
        }
    }

    std::shared_ptr<rclcpp::Node> node_;
    std::shared_ptr<MoveGroupInterface> arm_;
    std::shared_ptr<MoveGroupInterface> gripper_;

    rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_state_sub_;

    std::mutex mtx_;
    std::vector<std::string> expected_joint_names_;
    std::vector<double> latest_joint_positions_;
    bool received_joint_state_;
};

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("roarm_commander");
    Commander commander(node);

    RCLCPP_INFO(node->get_logger(), "Commander started, reading /joint_states locally.");
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
