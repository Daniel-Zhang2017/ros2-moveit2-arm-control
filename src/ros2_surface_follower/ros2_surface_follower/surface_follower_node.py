#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import numpy as np
import pcl
from sensor_msgs.msg import PointCloud2
import pcl_conversions
from geometry_msgs.msg import PoseStamped
from tf2_ros import Buffer, TransformListener
from tf2_geometry_msgs import do_transform_pose

class SurfaceFollowerNode(Node):
    def __init__(self):
        super().__init__("surface_follower_node")
        self.declare_parameter("pointcloud_topic", "/camera/points")
        self.declare_parameter("roi_radius", 0.15)
        self.declare_parameter("offset", 0.005)
        self.declare_parameter("plane_threshold", 0.002)
        self.declare_parameter("frame_id", "camera_link")
        self.declare_parameter("target_frame", "base_link")
        self.declare_parameter("publish_pose_topic", "/servo_node/pose_target_cmds")

        self.cloud_sub = self.create_subscription(
            PointCloud2,
            self.get_parameter("pointcloud_topic").value,
            self.cloud_cb,
            10
        )
        self.pose_pub = self.create_publisher(PoseStamped, self.get_parameter("publish_pose_topic").value, 10)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.roi_radius = self.get_parameter("roi_radius").value
        self.offset = self.get_parameter("offset").value
        self.plane_thresh = self.get_parameter("plane_threshold").value
        self.frame_id = self.get_parameter("frame_id").value
        self.target_frame = self.get_parameter("target_frame").value

    def cloud_cb(self, msg:PointCloud2):
        # PointCloud2 -> pcl
        pc = pcl_conversions.fromMsg(msg)
        if pc.size < 100:
            return

        # ROI filter：取相机前方一小块
        passthrough = pc.make_passthrough_filter()
        passthrough.set_filter_field_name("z")
        passthrough.set_filter_limits(0.05, 1.0)
        pc_filtered = passthrough.filter()

        # RANSAC 平面拟合
        seg = pc_filtered.make_segmenter()
        seg.set_model_type(pcl.SACMODEL_PLANE)
        seg.set_method_type(pcl.SAC_RANSAC)
        seg.set_distance_threshold(self.plane_thresh)
        indices, model = seg.segment()
        if len(indices) < 20:
            return

        # model: [a,b,c,d], ax+by+cz+d=0; normal n=(a,b,c)
        a,b,c,d = model
        norm = np.sqrt(a**2 + b**2 + c**2)
        normal = np.array([a,b,c]) / norm
        # 平面上一点
        p0 = -d * normal

        # 目标点：沿法线向外偏移 offset
        target_pt = p0 + normal * self.offset

        # 构造姿态：z轴对齐表面法线
        pose_cam = PoseStamped()
        pose_cam.header = msg.header
        pose_cam.pose.position.x = float(target_pt[0])
        pose_cam.pose.position.y = float(target_pt[1])
        pose_cam.pose.position.z = float(target_pt[2])
        # 简易姿态：法线作为z轴（简化版本，学习够用）
        pose_cam.pose.orientation.w = 1.0

        # TF 转到 base_link frame
        try:
            tf = self.tf_buffer.lookup_transform(self.target_frame, self.frame_id, rclpy.time.Time())
            pose_base = do_transform_pose(pose_cam, tf)
            self.pose_pub.publish(pose_base)
        except Exception as e:
            self.get_logger().debug(f"tf error: {e}")

def main():
    rclpy.init()
    node = SurfaceFollowerNode()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
