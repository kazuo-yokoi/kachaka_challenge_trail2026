import math
from collections import deque
import numpy as np

import angles
import rclpy
from geometry_msgs.msg import Twist
from kachaka_interfaces.msg import ObjectDetection, ObjectDetectionListStamped
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_srvs.srv import SetBool
from std_msgs.msg import Bool

MAX_RANGE_FOR_FOLLOW = 1.0
ANGULAR_TOLERANCE = 0.8

#静止検出用のパラメータ
STOP_DETECTION_DURATION_SEC = 10 #何秒間の静止で停止と判断するか
STOP_DETECTION_THRESHOLD = 0.05  #位置の標準偏差の閾値


class Follower(Node):
    def __init__(self) -> None:
        super().__init__("follow")

        # -- 追従制御関連 -- 
        self._is_enabled = False
        self._host_stopped = False

        # -- Publisher / Subscriber / Service --
        self._publisher = self.create_publisher(
            Twist, "/kachaka/manual_control/cmd_vel", 10
        )
        self._lidar_subscriber = self.create_subscription(
            LaserScan, "/kachaka/lidar/scan", self._laser_scan_callback, 10
        )
        self._object_detection_subscriber = self.create_subscription(
            ObjectDetectionListStamped,
            "/kachaka/object_detection/result",
            self._object_detection_callback,
            10,
        )
        self._stopped_publisher = self.create_publisher(
            Bool, "/follower/host_stopped", 10
        ) #ホストが止まったかどうかをpublishする
        self.create_service(
            SetBool, "/follower/set_enabled", self._set_enabled_callback
        ) #追跡を開始するかどうかを受け取り、追跡を開始する

        self._timer = self.create_timer(0.1, self._publish_cmd_vel)
        self._cmd_vel = Twist()
        self._closest_distance = float("inf")
        self._closest_angle = 0.0
        self._person_in_detection = False

        #-- 静止検出用変数 --
        history_size = int(STOP_DETECTION_DURATION_SEC/ 0.1)
        self._position_history = deque(maxlen=history_size)

    def _set_enabled_callback(self, request: SetBool.Request, response: SetBool.Response) -> SetBool.Response:
        """追跡の有効/無効を切り替えるサービスコールバック"""
        self._is_enabled = request.data
        self.get_logger().info(f"Following enabled has been set to: {self._is_enabled}")

        if not self._is_enabled:
            #停止の指示の場合、速度をゼロにし、状態をリセット
            self._cmd_vel = Twist()
            self._publisher.publish(self._cmd_vel)
            self._host_stopped = False
            self._person_in_detection = False
            self._position_history.clear()
            
        response.success = True
        return response

    def _check_for_stop_signal(self):
        """ホストの静止を検出する"""
        if len(self._positon_history) < history_size:
            return
        #x,y座標の標準偏差を計算
        positions = np.array(self._positon_history)
        std_dev = np.std(positions, axis=0)
        #x,y座標のばらつきが閾値以下なら静止と判断
        if np.all(std_dev < STOP_DETECTION_THRESHOLD):
            if not self.host_stopped:
                self.get_logger().info('Host has stopped. Stop following')
                self._host_stopped = True
                msg = Bool()
                msg.bool = True
                self._stopped_publisher.publish(msg)
            
    def _publish_cmd_vel(self) -> None:
        """速度指令をPublishするメインループ"""
        #追跡が無効、またはホストが停止した場合は何もしない
        if not self._is_enabled or self._host_stopped:
            if self._cmd_vel.linear.x != 0.0 or self._cmd_vel.angular.z != 0.0:
                self._cmd_vel.linear.x = 0.0
                self._cmd_vel.angular.z = 0.0
                self._publish_cmd_vel.publish(self._cmd_vel)
                return
        #人が検出されていない場合も停止
        if not self._person_in_detection:
            self.get_logger().info("no person")
            self._cmd_vel.linear.x = 0.0
            self._cmd_vel.angular.z = 0.0
            self._publisher.publish(self._cmd_vel)
            return

        #-- 静止検出 --
        self._check_for_stop_signal(self)
        if self._host_stopped:
            return
        #-- 追跡 --
        self.get_logger().info("publish")
        self.get_logger().info(f"{self._closest_angle=}")
        self._cmd_vel.linear.x = 0.0
        self._cmd_vel.angular.z = 0.0
        if 0.3 < self._closest_angle < ANGULAR_TOLERANCE:
            self.get_logger().info("turn right")
            self._cmd_vel.angular.z = 1.0
        elif -0.3 > self._closest_angle > -ANGULAR_TOLERANCE:
            self.get_logger().info("turn left")
            self._cmd_vel.angular.z = -1.0
        else:
            if self._closest_distance < MAX_RANGE_FOR_FOLLOW:
                self.get_logger().info("go foward")
            self._cmd_vel.linear.x = 0.3
        self._publisher.publish(self._cmd_vel)

    def _laser_scan_callback(self, msg: LaserScan) -> None:
        ranges = msg.ranges
        valid_ranges = [r for r in ranges if r > 0]
        if not valid_ranges:
            return

        min_range = min(valid_ranges)
        min_index = ranges.index(min_range)
        angle_increment = msg.angle_increment
        self._closest_distance = min_range
        self._closest_angle = angles.normalize_angle(
            msg.angle_min + (min_index * angle_increment) + (math.pi / 2)
        )
        # 静止検出のために、極座標系からロボットを中心とした直交座標系に変換
        pos_x = self._closest_distance * math.cos(self._closest_angle)
        pos_y = self._closest_distance * math.sin(self._closest_angle)
        self._position_history.append((pos_x, pos_y))

    def _object_detection_callback(
        self, detections: ObjectDetectionListStamped
    ) -> None:
        is_person_found = any(
            obj.label == ObjectDetection.PERSON for obj in detections.detection
        )
        if is_person_found and not self._person_detected_start_time:
            self.get_logger().info('Person detected. Start tracking.')
            self._positon_history.clear() #新たに人が見つかった時に履歴をクリアする
        self._person_in_detection = is_person_found


def main(args=None):
    rclpy.init(args=args)
    follower = Follower()
    rclpy.spin(follower)
    follower.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()