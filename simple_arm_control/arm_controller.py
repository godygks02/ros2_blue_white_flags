# arm_controller.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json

class MultiArmForwarder(Node):
    def __init__(self):
        super().__init__('multi_arm_forwarder')
        
        self.robots = {
            "blue": {"name": "robot1"},
            "white": {"name": "robot2"}
        }

        self.command_sub = self.create_subscription(String, 'game_commands', self.json_command_callback, 10)
        
        for r_id, info in self.robots.items():
            info['pub_goal'] = self.create_publisher(String, f'/{info["name"]}/goal', 10)

        # ⚠️ 시작 시 1.5초 후에 초기 위치(home)로 이동시키는 타이머 생성 (일회성)
        self.init_timer = self.create_timer(1.5, self.send_initial_home)
        self.get_logger().info('=== Multi-Arm Forwarder Ready (Startup Home Enabled) ===')

    def send_initial_home(self):
        """시작 시 로봇들을 중앙(0.5)으로 보냅니다."""
        self.get_logger().info('Sending initial home command to all robots...')
        for r_id, info in self.robots.items():
            msg = String()
            msg.data = "home"
            info['pub_goal'].publish(msg)
        
        # 타이머를 한 번 실행 후 정지
        self.init_timer.cancel()

    def json_command_callback(self, msg):
        try:
            data = json.loads(msg.data)
            commands = data.get('commands', []) if isinstance(data, dict) else data
            
            if not isinstance(commands, list): return

            for cmd in commands:
                r_id = cmd.get('id')
                action = cmd.get('action')
                if r_id in self.robots:
                    msg_out = String()
                    msg_out.data = action
                    self.robots[r_id]['pub_goal'].publish(msg_out)
                    self.get_logger().info(f'Forwarded: {r_id} -> {action}')
                    
        except Exception as e:
            self.get_logger().error(f'JSON Parsing Error: {e}')

def main(args=None):
    rclpy.init(args=args)
    node = MultiArmForwarder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
