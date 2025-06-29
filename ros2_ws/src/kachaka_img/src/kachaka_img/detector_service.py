#トピックに送られてくる画像をサブスクライブし、推論結果をパブリッシュするノード
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from sensor_msgs.msg import CompressedImage
from cv_bridge import CvBridge
from ultralytics import YOLO
from kachaka_ros2_dev_kit.kachaka_interfaces.msg import ObjectDetection, ObjectDetectionListStamped
from sensor_msgs.msg import RegionOfInterest 

class HumanDetector(Node):
    def __init__(self):
        super().__init__('human_detector')

        qos_profile = QoSProfile(
            reliability = ReliabilityPolicy.BEST_EFFORT,
            depth = 10
        )
        self.subscription = self.create_subscription(
            CompressedImage, 
            '/kachaka/front_camera/image_raw/compressed', 
            self.process_image,
            qos_profile
        )  
        self.publisher = self.create_publisher(
            ObjectDetectionListStamped,
            '/kachaka/object_detection/result', #このトピックおよびメッセージの型は使えるのか
            10 #queue sizeの設定はどうすれば良いか
        )
        self.cv_bridge = CvBridge()
        self.model = YOLO('yolov11n.pt')

    def process_image(self, msg):
        """受け取った画像を処理するコールバック関数"""
        np_arr = np.frombuffer(msg.data, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        results = self.model(image)
        boxes = results[0].boxes
        msg_array = ObjectDetectionListStamped()

        for i in range(len(boxes)):
            if boxes.cls[i] != 0:
                continue
            msg = ObjectDetection()
            msg.label = int(boxes.cls[i])    
            msg.score = float(boxes.conf[i])
            roi = RegionOfInterest()
            roi.x_offset = int(boxes.xyxy[i][0])
            roi.y_offset = int(boxes.xyxy[i][1])
            roi.height = int(boxes.xyxy[i][3]-boxes.xyxy[i][1])
            roi.width = int(boxes.xyxy[i][2]-boxes.xyxy[i][0])
            msg.roi = roi
            msg_array.detection.append(msg)

        self.publisher.publish(msg_array)

def main(args=None):
    rclpy.init(args=args)
    human_detector = HumanDetector()
    rclpy.spin(human_detector)
    rclpy.shutdown()

if __name__ = '__main__':
    main()
