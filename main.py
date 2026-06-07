# main.py
import json
import threading
import queue
import time
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
    print("=" * 55)
    print("  🤖 청기백기 Push-to-Talk 파이프라인 (ROS 2)")
    print("     ■ 스페이스바 누르고 있는 동안 말하기")
    print("     ■ 스페이스바 떼면 자동으로 인식 & 실행")
    print("     ■ 종료: Ctrl+C")
    print("=" * 55)

    rclpy.init()
    node = CommandPublisher()

    command_queue = queue.Queue()
    stop_event    = threading.Event()

    stt_thread = threading.Thread(
        target=continuous_listen,
        args=(command_queue, stop_event),
        daemon=True,
    )
    stt_thread.start()

    try:
        while rclpy.ok():
            # 큐에서 STT 결과 텍스트 꺼내기
            try:
                raw_text = command_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # LLM → 순차 명령 배열
            commands = process_text_to_commands(raw_text)
            if not commands:
                print("⚠️ 인식된 명령이 없습니다.")
                continue

            # ROS 2 토픽으로 명령 발행 (JSON 배열 형태)
            node.publish_commands(commands)
            
            # rclpy 콜백 처리 (필요할 경우를 대비)
            rclpy.spin_once(node, timeout_sec=0)

    except KeyboardInterrupt:
        print("\n\n🛑 [시스템] 종료 신호. 스레드 정리 중...")
        stop_event.set()
        stt_thread.join(timeout=3)
    finally:
        node.destroy_node()
        rclpy.shutdown()
        print("✅ 프로그램이 안전하게 종료되었습니다.")

if __name__ == "__main__":
    main()
