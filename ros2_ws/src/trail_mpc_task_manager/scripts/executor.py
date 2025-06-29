from kachaka_utils.position_helper import get_named_pose
from kachaka_utils.nav_manager import NavManager
from kachaka_utils.voice_manager import VoiceManager
from trail_mpc_task_manager.wait_for_host_ready import WaitForHostReady

import rclpy
from rclpy.node import Node
from std_srvs.srv import SetBool


class PartyTaskExecutor(Node):
    def __init__(self):
        super().__init__('party_task_executor')
        self.state = 'go_to_host_room'
        self.nav_manager = NavManager(self)
        self.voice_manager = VoiceManager(self)
        self.wait_state = WaitForHostReady(self,self.voice_manager)

        #--- followノード制御用のクライアントとサブスクライバー ---
        self._set_follow_client = self.create_client(SetBool, "/follower/set_enabled")
        while not self._set_follow_client.wait_for_service(timeout_sec = 0.1):
            self.get_logger().info('Follower service not available, waiting again...')
        self._stop_follower_subscriber = self.create_subscription(
            Bool, "/follower/host_stopped", self._host_stopped_callback, 10
        )
        self._follow_started = False

        # --- メインループタイマー ---
        self.timer = self.create_timer(1.0, self._main_loop)

    def _set_following_enabled(self, enabled: bool):
        """追従ノードの有効/無効をリクエストする"""
        req = SetBool.Request()
        req.data = enabled
        future = self._set_follow_client.call_async(req)
        self.get_logger().info(f"Requested to set following to {enabled}.")
    
    def _host_stopped_callback(self, msg: Bool):
        """追従停止の通知を受け取るコールバック"""
        if self.state == 'follow_host' and msg.data:
            self.get_logger().info("Stop signal received from follower node.")
            self._set_following_enabled(False) # 追従を停止させる
            self.state = 'go_to_entrance' # 次の状態に遷移
            self.get_logger().info("State changed to: go_to_entrance")

    def _main_loop(self):
        if self.state == 'go_to_host_room':
            self.get_logger().info("Going to host room...")
            pose = get_named_pose('host_room')
            self.nav_manager.go_to_pose(pose)  # 座標名 or PoseStamped
            self.state = 'wait_for_host_ready'
        elif self.state == 'wait_for_host_ready':
            self.get_logger().info("Waiting for host to be ready...")
            if not hasattr(self, '_wait_started'):
                self.wait_state.start()
                self._wait_started = True
                self.voice_manager.speak('10秒間そのままでいてください')
            if self.wait_state.update():
                self.state = 'follow_host'
                del self._wait_started
        elif self.state == 'follow_host':
            if not self._follow_started:
                self.get_logger().info('State: follow_host. Starting...')
                self._set_following_enabled(True) # 追従を開始させる
                self._follow_started = True
            self.get_logger().info("Now following host. Waiting for stop signal...", throttle_duration_sec=5)

            

        


def main(args=None):
    rclpy.init(args=args)
    executor = PartyTaskExecutor()
    rclpy.spin(executor)
    rclpy.shutdown()


if __name__ == '__main__':
    main()