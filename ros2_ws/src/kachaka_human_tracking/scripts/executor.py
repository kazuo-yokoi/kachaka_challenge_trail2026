#!usr/bin/env python3
import rclpy
import rclpy.logging

from kachaka_human_tracking.follow import (
    Follower,
)


def main():
    rclpy.init()
    human_follower_node = Follower()

    try:
        rclpy.spin(human_follower_node)
    except KeyboardInterrupt:
        rclpy.logging.get_logger("executor").info(
            "Keyboard interrupt, shutting down..."
        )
    finally:
        human_follower_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()