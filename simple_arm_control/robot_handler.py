# robot_handler.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
import time

class RobotHandlerNode(Node):
    def __init__(self):
        super().__init__('robot_handler_node')
        
        self.declare_parameter('robot_name', 'robot1')
        self.robot_name = self.get_parameter('robot_name').value

        # 병렬 처리를 위한 콜백 그룹 설정
        self.callback_group = ReentrantCallbackGroup()

        # 큐 및 상태
        self.action_queue = []
        self.is_busy = False
        self.wait_until = 0.0 # 다음 명령을 보낼 수 있는 시간

        # 서비스 클라이언트들 생성
        self.srv_clients = {
            'up': self.create_client(Trigger, f'/{self.robot_name}/up', callback_group=self.callback_group),
            'down': self.create_client(Trigger, f'/{self.robot_name}/down', callback_group=self.callback_group),
            'shake': self.create_client(Trigger, f'/{self.robot_name}/shake', callback_group=self.callback_group),
            'home': self.create_client(Trigger, f'/{self.robot_name}/home', callback_group=self.callback_group)
        }

        # 명령어 구독 (콜백 그룹 지정)
        self.sub_goal = self.create_subscription(
            String, f'/{self.robot_name}/goal', self.goal_callback, 10, 
            callback_group=self.callback_group
        )
        
        # 큐 처리 타이머 (0.1초 주기로 체크)
        self.create_timer(0.1, self.process_queue, callback_group=self.callback_group)
        
        self.get_logger().info(f'[{self.robot_name}] Handler Node (with Delay) Ready.')

    def goal_callback(self, msg):
        action = msg.data
        if action in self.srv_clients:
            self.action_queue.append(action)
            self.get_logger().info(f'[{self.robot_name}] Action Added: {action} (Queue: {len(self.action_queue)})')

    def process_queue(self):
        # 이미 동작 중이거나 큐가 비어있으면 중단
        if self.is_busy or not self.action_queue:
            return

        # ⚠️ 설정된 딜레이 시간이 지났는지 확인
        now = self.get_clock().now().nanoseconds / 1e9
        if now < self.wait_until:
            return

        action = self.action_queue.pop(0)
        client = self.srv_clients[action]

        if not client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error(f'Service {action} not available!')
            return

        self.is_busy = True
        self.get_logger().info(f'[{self.robot_name}] >>> Executing: {action}')
        
        request = Trigger.Request()
        future = client.call_async(request)
        future.add_done_callback(lambda f: self.service_done_callback(f, action))

    def service_done_callback(self, future, action):
        try:
            response = future.result()
            self.get_logger().info(f'[{self.robot_name}] <<< Finished: {action}')
            
            # ⚠️ 동작 완료 후 0.5초 대기 시간 설정
            self.wait_until = self.get_clock().now().nanoseconds / 1e9 + 0.5
            
        except Exception as e:
            self.get_logger().error(f'Service call failed: {e}')
        
        self.is_busy = False

def main(args=None):
    rclpy.init(args=args)
    node = RobotHandlerNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
