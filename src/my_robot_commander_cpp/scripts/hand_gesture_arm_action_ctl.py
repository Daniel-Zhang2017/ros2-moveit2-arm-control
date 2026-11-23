#!/usr/bin/env python3

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from my_robot_interfaces.action import ArmCommand

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import math


class HandGestureArmClient(Node):
    def __init__(self):
        super().__init__("hand_gesture_arm_client")
        self._client = ActionClient(self, ArmCommand, "/arm_command")

        MODEL_PATH = "src/my_robot_commander_cpp/hand_landmarker.task"
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

        self.target_pose = {
            "x": 0.45,
            "y": 0.0,
            "z": 0.25,
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
            "cartesian_path": False
        }

        self.last_gripper_state = None
        self.push_triggered = False
        self.z_threshold = -0.12
        self.stable_frames_required = 5
        self.stable_count = 0

        self.thumb_thresh = 0.22
        self.index_thresh = 0.30

        # Anti-false-positive: handedness confidence threshold
        self.min_handedness_score = 0.60

        self.get_logger().info(
            "Improved: handedness confidence + temporal filter to reduce false hand detection"
        )

    def send_gripper(self, open_gripper: bool):
        goal = ArmCommand.Goal()
        goal.command_type = 4
        goal.gripper_open = open_gripper
        self._send_goal_async(goal)

    def send_cartesian_move(self):
        goal = ArmCommand.Goal()
        goal.command_type = 2
        goal.x = self.target_pose["x"]
        goal.y = self.target_pose["y"]
        goal.z = self.target_pose["z"]
        goal.roll = self.target_pose["roll"]
        goal.pitch = self.target_pose["pitch"]
        goal.yaw = self.target_pose["yaw"]
        goal.cartesian_path = self.target_pose["cartesian_path"]
        self.get_logger().info("Hand push detected → moving to target pose")
        self._send_goal_async(goal)

    def _send_goal_async(self, goal):
        if not self._client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error("Action server /arm_command not available")
            return
        self._client.send_goal_async(goal)

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

    def draw_landmarks(self, frame, landmarks):
        h, w, _ = frame.shape
        for lm in landmarks:
            px = int(lm.x * w)
            py = int(lm.y * h)
            cv2.circle(frame, (px, py), 4, (0, 255, 0), -1)

    def run(self):
        while rclpy.ok():
            ret, frame = self.cap.read()
            if not ret:
                self.get_logger().warn("Camera read error")
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.detector.detect(mp_image)

            gripper_open = False
            hand_forward = False
            gesture_text = "NO HAND DETECTED"
            dist_text = ""
            confidence_text = ""
            valid_hand = False

            if result.hand_landmarks:
                # Correct API: result.handedness[0][0].score
                handedness_score = result.handedness[0][0].score
                handedness_label = result.handedness[0][0].category_name

                if handedness_score > self.min_handedness_score:
                    lm_list = result.hand_landmarks[0]
                    self.draw_landmarks(frame, lm_list)
                    valid_hand = True

                    gripper_open, thumb_ext, index_ext, d_t, d_i = self.check_thumb_index_extended(lm_list)
                    palm_z = lm_list[0].z
                    hand_forward = palm_z < self.z_threshold

                    dist_text = f"Thumb: {d_t:.3f} | Index: {d_i:.3f}"
                    confidence_text = f"Handedness: {handedness_label} score={handedness_score:.3f}"

                    if gripper_open and hand_forward:
                        gesture_text = "PUSH FORWARD (Thumb+Index Open)"
                    elif gripper_open:
                        gesture_text = "OPEN GRIPPER (Thumb+Index Extended)"
                    else:
                        gesture_text = "CLOSE GRIPPER (Thumb/Index Bent)"
                else:
                    gesture_text = "REJECTED: low handedness confidence"

            cv2.putText(
                frame,
                f"Gesture: {gesture_text}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
                cv2.LINE_AA
            )
            cv2.putText(
                frame,
                dist_text,
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 0, 0),
                2,
                cv2.LINE_AA
            )
            cv2.putText(
                frame,
                confidence_text,
                (20, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                2,
                cv2.LINE_AA
            )

            if valid_hand:
                if gripper_open and self.last_gripper_state != "open":
                    self.send_gripper(True)
                    self.last_gripper_state = "open"
                elif not gripper_open and self.last_gripper_state != "closed":
                    self.send_gripper(False)
                    self.last_gripper_state = "closed"

                if gripper_open and hand_forward:
                    self.stable_count += 1
                    if self.stable_count >= self.stable_frames_required and not self.push_triggered:
                        self.send_cartesian_move()
                        self.push_triggered = True
                else:
                    self.stable_count = 0
                    self.push_triggered = False
            else:
                self.stable_count = 0
                self.push_triggered = False

            cv2.imshow("Gesture Control", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

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
