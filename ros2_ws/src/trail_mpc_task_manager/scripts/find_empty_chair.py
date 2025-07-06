#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.task import Future

from std_msgs.msg import Bool

import os
import numpy as np
from pathlib import Path

import cv2
from PIL import Image as PILImage
from ultralytics import YOLO

from geometry_msgs.msg import Twist

from kachaka_utils.camera_manager import CameraManager
from kachaka_utils.voice_manager import VoiceManager
from kachaka_utils.nav_manager import NavManager
from kachaka_utils.llm_manager import LLMManager

class FindEmptyChair(Node):
    def __init__(self) :
        super().__init__('find_empty_chair')
        self.camera_manager = CameraManager(self)
        self.voice_manager = VoiceManager(self)
        self.llm_manager = LLMManager()
        self.path = Path(__file__).resolve().parent.parent
        self.model = YOLO(self.path / "yolo11x.pt")

        self._publisher = self.create_publisher(
            Twist, "/kachaka/manual_control/cmd_vel", 10
        )

        self.start_subscriber = self.create_subscription(Bool, "/find_empty_chair/start", self._start_callback,10)
        self.end_publisher = self.create_publisher(Bool, "/find_empty_chair/end", 10)
        self.future = Future()

    def main(self) :
        while rclpy.ok() :
            self.future = Future()
            rclpy.spin_until_future_complete(self, self.future)
            self.execute_find_empty_chair()
            msg = Bool()
            msg.data =True
            self.end_publisher.publish(msg)

    def _start_callback(self, msg) :
        self.future.set_result(True)

    def turn_to_chair_test(self) :
        image, pil_image = self.camera_manager.get_image()
        result = self.model(image)[0]
        cv2.imshow("TEST",result.plot())
        cv2.waitKey(1)
        empty_i = self._get_empty_chair(result)
        if empty_i == -1 :
            self.get_logger().info("There is no empty chair.")
            return True
        self._turn_to_chair(float(result.boxes.xyxy[empty_i][0]+result.boxes.xyxy[empty_i][2])/2)
        return True


    def execute_find_empty_chair(self) :
        self.voice_manager.speak("空いている椅子を探します。", wait=True)
        image, pil_image = self.camera_manager.get_image()
        empty_i = -1
        result = None
        for direction in ("f", "l", "r") :
            self._turn_to(direction)
            result = self.model(image)[0]
            empty_i = self._get_empty_chair(result)
            if not empty_i == -1 : break
        if empty_i == -1 : 
            self.voice_manager.speak("空いている椅子が見つかりませんでした。各自で座ってください。", wait=True)
            return True

        self._turn_to_chair(float(result.boxes.xyxy[empty_i][0]+result.boxes.xyxy[empty_i][2])/2)
        self.voice_manager.speak("こちらの方向の椅子に座ってください。", wait=True)
        return True

    def _get_empty_chair(self, result) :
        persons = []
        for i in range(len(result)) :
            name = result.names[int(result.boxes.cls.int()[i])]
            if not name in ("person") : continue
            persons.append(result.boxes.xyxy[i])
        for i in range(len(result)) :
            name = result.names[int(result.boxes.cls.int()[i])]
            if not name in ("chair") : continue
            chair = result.boxes.xyxy[i]
            full_flag = False
            for j, person in enumerate(persons) :

                overlapped_size = (min(chair[2],person[2])-max(chair[0],person[0]))*(min(chair[3],person[3])-max(chair[1],person[1]))
                # self.get_logger().info(overlapped_size)
                if overlapped_size > (chair[2]-chair[0])*(chair[3]-chair[1])/2 or overlapped_size > (person[2]-person[0])*(person[3]-person[1])/2 :
                    full_flag = True
                    break
            if not full_flag :
                return i
        return -1
        
    def _turn_a_while(self, vel, sec) :
        _cmd_vel = Twist()
        _cmd_vel.angular.z = vel
        for i in range(int(sec/0.1)) :
            self._publisher.publish(_cmd_vel)
            self.get_clock().sleep_for(Duration(seconds=0.1))
        self._publisher.publish(Twist())

    def _turn_to(self, direction) :
        if direction == "f" :
            return 
        elif direction == "l" :
            self._turn_a_while(0.3, 3)
        elif direction == "r" :
            self._turn_a_while(-0.3, 6)
    
    def _turn_to_chair(self, coord) :
            self.get_logger().info(f"start")
            self._turn_a_while(0.3 if coord < 640 else -0.3, abs(coord-640)/165)
            self.get_logger().info(f"turn to chair coord:{coord}")
    
if __name__ == '__main__':
    rclpy.init()

    find_empty_chair = FindEmptyChair()

    find_empty_chair.main()

    find_empty_chair.destroy_node()
    rclpy.shutdown()