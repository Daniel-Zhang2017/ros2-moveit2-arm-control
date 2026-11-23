#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from example_interfaces.msg import Bool
from my_robot_interfaces.msg import PoseCommand

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import math
import os


class HandGestureArmClient(Node):
    def __init__(self):
        super().__init__("hand_gesture_arm_topic_ctl")

        # Publishers
        self.gripper_pub = self.create_publisher(Bool, "/open_gripper", 10)
        self.pose_pub = self.create_publisher(PoseCommand, "/pose_command", 10)

        # MediaPipe model: same scripts folder
        script_dir = os.path.dirname(os.path.abspath(__file__))
        MODEL_PATH = os.path.join(script_dir, "hand_landmarker.task")

        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.65,
            min_hand_presence_confidence=0.55,
            min_tracking_confidence=0.55
        )
        self.detector = vision.HandLandmarker.create_from_options(options)
        self.cap = cv2.VideoCapture(0)

        # Thumb + index distance thresholds
        self.thumb_thresh = 0.22
        self.index_thresh = 0.30
        self.min_handedness_score = 0.60

        # ===== Mapping range: normalized hand (0~1) -> robot base frame (meters) =====
        self.robot_x_min = 0.25
        self.robot_x_max = 0.65
        self.robot_y_min = -0.35
        self.robot_y_max = 0.35
        self.robot_z_min = 0.20
        self.robot_z_max = 0.70

        # Fixed end-effector orientation
        self.roll = 3.14159
        self.pitch = 0.0
        self.yaw = 0.0
        self.cartesian_path = False

        # Low-pass smoothing + deadzone
        self.alpha = 0.4
        self.deadzone = 0.015
        self.smooth_x = None
        self.smooth_y = None
        self.smooth_z = None

        # Cache latest detection result (updated every camera frame, published at 5Hz)
        self.valid_hand = False
        self.gripper_open = False
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_z = 0.0
        self.d_t = 0.0
        self.d_i = 0.0
        self.handedness_label = ""
        self.handedness_score = 0.0
        self.gesture_text = "NO HAND DETECTED"

        self.last_gripper_state = None

        # 5Hz timer (0.2 second period) for ROS publish
        self.pub_timer = self.create_timer(0.2, self.timer_publish_callback)

        self.get_logger().info(
            "Hand teleop topic control: detection at camera FPS, pose/gripper publish @ 5Hz"
        )

    def dist(self, a, b):
        return math.hypot(a.x - b.x, a.y - b.y)

    def check_thumb_index_extended(self, landmarks):
        wrist = landmarks[0]
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]

        d_thumb = self.dist(thumb_tip, wrist)
        d_index = self.dist(index_tip, wrist)

        thumb_extended = d_thumb > self.thumb_thresh
        index_extended = d_index > self.index_thresh
        gripper_open = thumb_extended and index_extended
        return gripper_open, thumb_extended, index_extended, d_thumb, d_index

    def map_range(self, val, in_min, in_max, out_min, out_max):
        return out_min + (val - in_min) * (out_max - out_min) / (in_max - in_min)

    def lowpass(self, prev, new_val):
        if prev is None:
            return new_val
        return self.alpha * new_val + (1 - self.alpha) * prev

    def draw_landmarks(self, frame, landmarks):
        h, w, _ = frame.shape
        for lm in landmarks:
            px = int(lm.x * w)
            py = int(lm.y * h)
            cv2.circle(frame, (px, py), 4, (0, 255, 0), -1)

    # 5Hz timer callback: publish cached pose + gripper
    def timer_publish_callback(self):
        if not self.valid_hand:
            return

        # Publish PoseCommand
        pose_msg = PoseCommand()
        pose_msg.x = self.robot_x
        pose_msg.y = self.robot_y
        pose_msg.z = self.robot_z
        pose_msg.roll = self.roll
        pose_msg.pitch = self.pitch
        pose_msg.yaw = self.yaw
        pose_msg.cartesian_path = self.cartesian_path
        self.pose_pub.publish(pose_msg)

        # Publish gripper only when state changes
        if self.gripper_open and self.last_gripper_state != True:
            gripper_msg = Bool()
            gripper_msg.data = True
            self.gripper_pub.publish(gripper_msg)
            self.last_gripper_state = True
        elif not self.gripper_open and self.last_gripper_state != False:
            gripper_msg = Bool()
            gripper_msg.data = False
            self.gripper_pub.publish(gripper_msg)
            self.last_gripper_state = False

    def run(self):
        while rclpy.ok():
            ret, frame = self.cap.read()
            if not ret:
                self.get_logger().warn("Camera read error")
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.detector.detect(mp_image)

            # Reset cache
            self.valid_hand = False
            self.gesture_text = "NO HAND DETECTED"
            dist_text = ""
            confidence_text = ""

            if result.hand_landmarks:
                handedness_score = result.handedness[0][0].score
                handedness_label = result.handedness[0][0].category_name

                if handedness_score > self.min_handedness_score:
                    lm_list = result.hand_landmarks[0]
                    self.draw_landmarks(frame, lm_list)

                    gripper_open, thumb_ext, index_ext, d_t, d_i = self.check_thumb_index_extended(lm_list)

                    # Wrist landmark (0) as hand reference
                    hand_x = lm_list[0].x
                    hand_y = lm_list[0].y
                    hand_z = lm_list[0].z

                    # Deadzone
                    if self.smooth_x is not None:
                        if abs(hand_x - self.smooth_x) < self.deadzone:
                            hand_x = self.smooth_x
                        if abs(hand_y - self.smooth_y) < self.deadzone:
                            hand_y = self.smooth_y
                        if abs(hand_z - self.smooth_z) < self.deadzone:
                            hand_z = self.smooth_z

                    # Low pass filter
                    self.smooth_x = self.lowpass(self.smooth_x, hand_x)
                    self.smooth_y = self.lowpass(self.smooth_y, hand_y)
                    self.smooth_z = self.lowpass(self.smooth_z, hand_z)

                    # Map to robot base frame
                    robot_x = self.map_range(self.smooth_x, 0.0, 1.0, self.robot_x_min, self.robot_x_max)
                    robot_y = self.map_range(1.0 - self.smooth_y, 0.0, 1.0, self.robot_y_min, self.robot_y_max)
                    robot_z = self.map_range(self.smooth_z, -0.3, 0.3, self.robot_z_min, self.robot_z_max)

                    # Save to cache for 5Hz publisher
                    self.valid_hand = True
                    self.gripper_open = gripper_open
                    self.robot_x = robot_x
                    self.robot_y = robot_y
                    self.robot_z = robot_z
                    self.d_t = d_t
                    self.d_i = d_i
                    self.handedness_label = handedness_label
                    self.handedness_score = handedness_score

                    dist_text = f"Thumb: {d_t:.3f} | Index: {d_i:.3f}"
                    confidence_text = f"Handed: {handedness_label} score={handedness_score:.3f}"

                    if gripper_open:
                        self.gesture_text = "TELEOP: Thumb+Index OPEN (Gripper Open)"
                    else:
                        self.gesture_text = "TELEOP: Thumb/Index BENT (Gripper Close)"
                else:
                    self.gesture_text = "REJECTED: low handedness confidence"
            else:
                # No hand, reset smoothing buffer
                self.smooth_x = None
                self.smooth_y = None
                self.smooth_z = None

            # Draw overlay text
            cv2.putText(frame, f"Gesture: {self.gesture_text}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2, cv2.LINE_AA)
            cv2.putText(frame, dist_text, (20, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,0,0), 2, cv2.LINE_AA)
            cv2.putText(frame, confidence_text, (20, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 2, cv2.LINE_AA)

            cv2.imshow("Gesture Teleop Topic Ctl", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break

            # Spin ROS timer so 5Hz callback runs
            rclpy.spin_once(self, timeout_sec=0.001)

        self.cap.release()
        cv2.destroyAllWindows()


def main():
    rclpy.init()
    node = HandGestureArmClient()
    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
