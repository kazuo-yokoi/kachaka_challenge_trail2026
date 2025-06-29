#!/usr/bin/env python3
import rclpy
import rclpy.logging

from kachaka_img.detector_service import (
    HumanDetector,
)


def main():
    rclpy.init()
    human_detector_node = HumanDetector()

    try:
        rclpy.spin(human_detector_node)
    except KeyboardInterrupt:
        rclpy.logging.get_logger("executor").info(
            "Keyboard interrupt, shutting down..."
        )
    finally:
        human_detector_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()