# main.py
import threading
import queue
import time
import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from stt_worker import continuous_listen
from llm_processor import process_text_to_commands

class CommandPublisher(Node):
    def __init__(self):
        super().__init__('voice_command_publisher')
        self.publisher_ = self.create_publisher(String, 'game_commands', 10)

    def publish_commands(self, commands_list):
        msg = String()
        msg.data = json.dumps(commands_list)
        self.publisher_.publish(msg)
        self.get_logger().info(f'Published commands: {msg.data}')

def main():
    print("=== 🤖 청기백기 게임 파이프라인 (ROS2 + OpenAI + 스페이스바 모드) ===")

    rclpy.init()
    node = CommandPublisher()

    command_queue = queue.Queue()
    stop_event = threading.Event()

    stt_thread = threading.Thread(
        target=continuous_listen, 
        args=(command_queue, stop_event), 
        daemon=True
    )
    stt_thread.start()

    try:
        while rclpy.ok():
            if not command_queue.empty():
                raw_text = command_queue.get()
                print(f"\n🧠 [OpenAI 처리 중] 입력 텍스트: '{raw_text}'")

                commands_list = process_text_to_commands(raw_text)

                if not commands_list:
                    continue

                # ROS2 토픽으로 명령 발행
                node.publish_commands(commands_list)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n🛑 [시스템] 종료 신호를 받았습니다. 스레드를 정리합니다...")
    finally:
        stop_event.set()
        stt_thread.join(timeout=2)
        node.destroy_node()
        rclpy.shutdown()
        print("✅ 프로그램이 안전하게 종료되었습니다.")

if __name__ == "__main__":
    main()