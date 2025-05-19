from geometry_msgs.msg import Pose, Point, Quaternion

from kachaka_utils.src.kachaka_utils.voice_manager import VoiceManager
from kachaka_utils.src.kachaka_utils.nav_manager import NavManager


class ExampleSubTaskManager1:
    def __init__(self, voice_manager: VoiceManager, nav_manager: NavManager) -> None:
        self.voice_manager = voice_manager
        self.nav_manager = nav_manager

    def execute_sub_task1(self) -> bool:
        self.voice_manager.speak("まず初めにサブタスク１を行います。")
        self.nav_manager.go_to_pose(
            Pose(position=Point(-0.3, 0, 0), orientation=Quaternion(0, 0, 0, 0))
        )

        return True
