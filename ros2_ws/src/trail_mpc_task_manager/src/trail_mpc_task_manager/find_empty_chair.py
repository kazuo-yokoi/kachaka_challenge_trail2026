import rclpy
from rclpy.duration import Duration

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

class FindEmptyChairTaskManager:
    def __init__(self, parent_node, camera_manager: CameraManager, voice_manager: VoiceManager, llm_manager: LLMManager) -> None:
        self.parent_node = parent_node
        self.camera_manager = camera_manager
        self.voice_manager = voice_manager
        self.llm_manager = llm_manager
        self.path = Path(__file__).resolve().parent.parent.parent.parent
        self.model = YOLO(self.path / kachaka_img / "yolo11n.pt")

        self._publisher = self.parent_node.create_publisher(
            Twist, "/kachaka/manual_control/cmd_vel", 10
        )

    def camera_test(self) :
        image, pil_image = self.camera_manager.get_image()
        result = self.model(image)[0]
        persons = []
        for i in range(len(result)) :
            name = result.names[int(result.boxes.cls.int()[i])]
            if not name in ("person") : continue
            persons.append(result.boxes.xyxy[i])
        for i in range(len(result)) :
            name = result.names[int(result.boxes.cls.int()[i])]
            if not name in ("chair") : continue
            chair = result.boxes.xyxy[i]
            for i, person in enumerate(persons) :

                overlapped_size = min(chair[2],person[2])-max(chair[0],person[0])*min(chair[3],person[3])-max(chair[1],person[1])
                if overlapped_size > (chair[2]-chair[0])*(chair[3]-chair[1]) or overlapped_size > (person[2]-person[0])*(person[3]-person[1]) :
                    return i
                self.parent_node.get_logger.info(min(chair[2],person[2])-max(chair[0],person[0])*min(chair[3],person[3])-max(chair[1],person[1]))
            # self.parent_node.get_logger().info(f"name:{name}, p:{result.boxes.conf}, xyxy:{result.boxes.xyxy}")
        # answer = self.llm_manager.infer(["Guide me to an empty chair", pil_image])
        # answer2 = self.llm_manager.infer(["output whether the chairs in the picture are empty", pil_image], self.tools)
        # answer2 = self.llm_manager.infer(["Answer whether there is a empty chair. If there is a empty chair, answer the side of the image a empty chair is on.", pil_image], self.tools)
        # answer2 = dict(answer2.candidates[0].content.parts[0].function_call.args)
        # self.parent_node.get_logger().info(answer.text)
        # self.parent_node.get_logger().info(str(answer2))
        # self.camera_manager.save_image(image)
        return True

    def turn_to_chair_test(self) :
        image, pil_image = self.camera_manager.get_image()
        result = self.model(image)[0]
        cv2.imshow("TEST",result.plot())
        cv2.waitKey(1)
        empty_i = self._get_empty_chair(result)
        if empty_i == -1 :
            self.parent_node.get_logger().info("There is no empty chair.")
            return True
        self._turn_to_chair(float(result.boxes.xyxy[empty_i][0]+result.boxes.xyxy[empty_i][2])/2)
        self.parent_node.get_logger().info(str(float(result.boxes.xyxy[empty_i][0]+result.boxes.xyxy[empty_i][2])/2))
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
                # self.parent_node.get_logger().info(overlapped_size)
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
            self.parent_node.get_clock().sleep_for(Duration(seconds=0.1))
        self._publisher.publish(Twist())

    def _turn_to(self, direction) :
        if direction == "f" :
            return 
        elif direction == "l" :
            self._turn_a_while(0.3, 2)
        elif direction == "r" :
            self._turn_a_while(-0.3, 4)

    def _turn_to_chair(self, coord) :
            self.parent_node.get_logger().info(f"start")
            self._turn_a_while(0.3 if coord < 640 else -0.3, abs(coord-640)/150)
            self.parent_node.get_logger().info(f"turn to chair coord:{coord}")