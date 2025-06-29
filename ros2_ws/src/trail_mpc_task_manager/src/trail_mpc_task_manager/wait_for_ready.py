from kachaka_utils.voice_manager import VoiceManager
from kachaka_interfaces.msg import ObjectDetection, ObjectDetectionListStamped

from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time

class WaitForHostReady:
    def __init__(self, parent_node: Node, voice_manager: VoiceManager):
        self.parent_node = parent_node
        self.voice_manager = voice_manager

        self._person_detected_start_time = None
        self._person_in_detection = False

        self.parent_node.create_subscription(
            ObjectDetectionListStamped,
            "/kachaka/object_detection/result",
            self._object_detection_callback,
            qos_profile_sensor_data,
        )
        
    def start(self):
        self.voice_manager.speak('準備ができたらカメラの前に立ってください')

    def update(self):
        if self._person_in_detection:
            if self._person_detected_start_time is None:
                self._person_detected_start_time = self.parent_node.get_clock().now()
            else:
                elapsed = (self.node.get_clock().now() - self._person_detected_start_time).nanoseconds/1e9
                if elapsed >= 10:
                    self.voice_manager.speak('追従を開始します。パーティー会場まで歩いてください')
                    return True
        else:
            self._person_detected_start_time = None
        return False     
        
    def _object_detection_callback(self, detections: ObjectDetectionListStamped) -> None:
        self._person_in_detection = any(
            obj.label == ObjectDetection.PERSON for obj in detections.detection
        )
