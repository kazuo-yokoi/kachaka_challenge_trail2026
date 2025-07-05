import rclpy
from rclpy.task import Future
from rclpy.qos import QoSProfile, ReliabilityPolicy

import os
import numpy as np
from pathlib import Path

import cv2
from PIL import Image as PILImage
from sensor_msgs.msg import CompressedImage

class CameraManager:
    def __init__(self, parent_node) -> None:
        self.parent_node = parent_node
        self.future = Future()
        self.path = Path(__file__).resolve().parent.parent.parent
        qos_profile = QoSProfile(
            reliability = ReliabilityPolicy.BEST_EFFORT,
            depth = 10
        )
        self.subscription = self.parent_node.create_subscription(
            CompressedImage, 
            '/kachaka/front_camera/image_raw/compressed',
            self._camera_callback,
            qos_profile)

    def save_image(self, image) :
        files = os.listdir(self.path / "images")
        file_nums = map (lambda x :int(x[:-4]), files)
        cv2.imwrite(self.path / "images" / (str(max(file_nums)+1)+".jpg"), image)

    def get_image(self) :
        self.future = Future()
        # self.parent_node.get_logger().info("Waiting for image...")
        rclpy.spin_until_future_complete(self.parent_node, self.future)
        raw_image = self.future.result()
        image = self._compressed_img_to_cv2(raw_image)
        pil_image = PILImage.fromarray(image)
        return image, pil_image

    def _compressed_img_to_cv2(self, compressed_image):
        np_arr = np.frombuffer(compressed_image.data, np.uint8)
        image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        return image

    def _camera_callback(self, msg) :
        # self.parent_node.get_logger().info("get_image")
        if not self.future.done():
            self.future.set_result(msg)