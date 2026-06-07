# arm_controller.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import json
from functools import partial

class MultiArmBrainController(Node):
    def __init__(self):
        super().__init__('multi_arm_brain_controller')
        
        # 설정: 로봇 ID와 네임스페이스 매핑
        self.robots = {
            "blue": {"name": "robot1", "status": "IDLE", "queue": []},
            "white": {"name": "robot2", "status": "IDLE", "queue": []}
        }

        # 토픽 설정
        self.command_sub = self.create_subscription(String, 'game_commands', self.json_command_callback, 10)
        
        for r_id, info in self.robots.items():
            name = info['name']
            # 명령 전송용 퍼블리셔
            info['pub_goal'] = self.create_publisher(String, f'/{name}/goal', 10)
            # 상태 모니터링 구독자
            self.create_subscription(
                String, 
                f'/{name}/status', 
                partial(self.status_callback, robot_id=r_id), 
                10
            )

        # 큐를 주기적으로 체크하여 명령을 전달하는 타이머
        self.create_timer(0.1, self.process_queues)
        self.get_logger().info('=== Multi-Arm Brain Controller (Queue Master) Ready ===')

    def status_callback(self, msg, robot_id):
        """로봇의 실시간 상태(IDLE/BUSY) 업데이트"""
        self.robots[robot_id]['status'] = msg.data

    def json_command_callback(self, msg):
        """AI 명령을 수신하여 각 로봇의 큐에 추가"""
        try:
            data = json.loads(msg.data)
            commands = data.get('commands', []) if isinstance(data, dict) else data
            
            if not isinstance(commands, list): return

            self.get_logger().info(f'Received {len(commands)} commands. Adding to queues...')
            for cmd in commands:
                r_id = cmd.get('id')
                action = cmd.get('action')
                if r_id in self.robots:
                    self.robots[r_id]['queue'].append(action)
                    self.get_logger().info(f'  - Queued: {r_id} -> {action} (Total: {len(self.robots[r_id]["queue"])})')
                    
        except Exception as e:
            self.get_logger().error(f'JSON Parsing Error: {e}')

    def process_queues(self):
        """모든 로봇을 확인하고, IDLE 상태인 로봇에게 큐의 다음 명령을 전송"""
        for r_id, info in self.robots.items():
            # 로봇이 완전히 IDLE 상태이고, 큐에 명령이 있다면 실행
            if info['status'] == "IDLE" and info['queue']:
                # ⚠️ 즉시 상태를 BUSY로 변경하여 0.1초 내에 다음 명령이 발송되는 것을 방지
                info['status'] = "SENDING" 
                
                next_action = info['queue'].pop(0)
                
                msg = String()
                msg.data = next_action
                info['pub_goal'].publish(msg)
                
                self.get_logger().info(f'>>> [GOAL SENT] {info["name"]} -> {next_action}')

def main(args=None):
    rclpy.init(args=args)
    node = MultiArmBrainController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
