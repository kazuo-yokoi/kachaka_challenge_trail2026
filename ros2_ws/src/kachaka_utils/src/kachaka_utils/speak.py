import rclpy
from kachaka_interfaces.action import ExecKachakaCommand
from kachaka_interfaces.msg import KachakaCommand
from rclpy.action import ActionClient
from rclpy.node import Node
from trail_kachaka_msgs.srv import KachakaSpeak


class Speak(Node):
    def __init__(self) -> None:
        super().__init__("kachaka_speak_node")
        self._action_client = ActionClient(
            self, ExecKachakaCommand, "/kachaka/kachaka_command/execute"
        )
        self._action_client.wait_for_server()

        self.speak_srv = self.create_service(
            KachakaSpeak, "/kachaka/speak", self.speak_callback
        )
        self.get_logger().info("Speak service is ready.")

    def speak_callback(self, request, response):
        self.get_logger().info(
            f"Received request: text: {request.text}, wait: {request.wait}"
        )
        try:
            command = KachakaCommand()
            command.command_type = KachakaCommand.SPEAK_COMMAND
            command.speak_command_text = request.text
            goal_msg = ExecKachakaCommand.Goal()
            goal_msg.kachaka_command = command
            if request.wait:
                self._action_client.send_goal_async(goal_msg)
            else:
                self._action_client.send_goal(goal_msg)
        except Exception as e:
            self.get_logger().error(f"Failed to send goal: {e}")
            response.success = False
            return response
        response.success = True
        return response


def main(args=None):
    rclpy.init(args=args)
    speak_node = Speak()
    try:
        rclpy.spin(speak_node)
    except KeyboardInterrupt:
        speak_node.get_logger().info("Keyboard interrupt, shutting down...")
    finally:
        speak_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
