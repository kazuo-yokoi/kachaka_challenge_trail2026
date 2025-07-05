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

from kachaka_utils.camera_manager import CameraManager
from kachaka_utils.voice_manager import VoiceManager
from kachaka_utils.llm_manager import LLMManager

class GuestMeetTaskManager(Node):
    def __init__(self):
        super().__init__('guest_meet')
        self.camera_manager = CameraManager(self)
        self.voice_manager = VoiceManager(self)
        self.llm_manager = LLMManager()
        self.path = Path(__file__).resolve().parent.parent
        self.tools = [{
            "function_declarations": [{
                "name": "parse_detection",
                "description": "Detect whether a person is present and whether upper body is visible",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "isThereAnyHuman": { "type": "boolean" },
                        "isHumansUpperBodyVisible": { "type": "boolean" }
                    },
                    "required": ["isThereAnyHuman", "isHumansUpperBodyVisible"]
                }
            }]
        }]
        self.start_subscriber = self.create_subscription(Bool, "/guest_meet/start", self._start_callback,10)
        self.end_publisher = self.create_publisher(Bool, "/guest_meet/end", 10)
        self.future = Future()

    def main(self) :
        while rclpy.ok() :
            self.future = Future()
            rclpy.spin_until_future_complete(self, self.future)
            # --- 修正 ---
            msg = Bool()
            msg.data = self.execute_guest_meet()
            self.end_publisher.publish(msg) 

    def _start_callback(self, msg) :
        self.future.set_result(True)

    def execute_guest_meet(self) :
        self.voice_manager.speak("ゲストは、私のカメラの前に2m程度離れて立ってください。", wait=True)
        for i in range(5) :
            self.parent_node.get_clock().sleep_for(Duration(seconds=3))
            image, pil_image = self.camera_manager.get_image()
            answer = self._recognize_human(pil_image)
            if not answer["isThereAnyHuman"] :
                self.voice_manager.speak("人が認識されていません。カメラの前に立ってください。")
            elif not answer["isHumansUpperBodyVisible"] :
                self.voice_manager.speak("カメラに近いです。カメラから離れてください。")
            else : 
                self.camera_manager.save_image(image)
                break

        answer = self.llm_manager.infer(["私のシャツ、ズボン、靴下を一行で説明してください。", pil_image])
        # self.parent_node.get_logger().info(answer.text)
        self.voice_manager.speak(answer.text)
        return True

    def _recognize_human(self, pil_image) :
        answer = self.llm_manager.infer(["Answer whether you can see a person and whether their upper body", pil_image], self.tools)
        return dict(answer.candidates[0].content.parts[0].function_call.args)

if __name__ == '__main__':
    rclpy.init()

    guest_meet = GuestMeet()

    guest_meet.main()

    guest_meet.destroy_node()
    rclpy.shutdown()