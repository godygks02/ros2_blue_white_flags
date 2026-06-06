import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64, String
from builtin_interfaces.msg import Duration
from functools import partial
import json
from . import action_flag

class RobotActionHandler:
    """
    각 로봇의 '상태'와 '동작(up/down/return)' 로직을 관리하는 클래스
    """
    def __init__(self, node, robot_name, joint_name, pub):
        self.node = node
        self.robot_name = robot_name
        self.joint_name = joint_name
        self.pub = pub
        
        self.current_height = 0.5
        self.cmd_height = 0.5
        self.target_height = 0.5
        self.home_height = 0.5
        
        self.step_size = 0.02
        self.is_moving = False
        self.returning_home = False
        self.initialized = False

    def update_current_height(self, pos):
        self.current_height = pos
        if not self.initialized:
            self.cmd_height = pos
            # 초기 목표 위치를 0.5로 강제 설정하여 시작하자마 +마자 이동하게 함
            self.target_height = 0.5
            self.home_height = 0.5
            self.is_moving = True
            self.returning_home = True # 홈으로 가는 상태로 간주
            self.initialized = True
            self.node.get_logger().info(f'[{self.robot_name}] Initializing: Moving from {pos:.2f} to home (0.5)')

    def start_action(self, action_type):
        """명령어(up/down)에 따른 목표치 설정"""
        self.target_height = action_flag.get_action_target(action_type)
        
        self.is_moving = True
        self.returning_home = False
        self.node.get_logger().info(f'[{self.robot_name}] Starting {action_type} to {self.target_height}')

    def step(self):
        """타이머에 의해 주기적으로 호출되는 이동 로직"""
        if not self.initialized: return

        diff = self.target_height - self.cmd_height
        
        # 목표 도달 확인
        if abs(diff) <= self.step_size:
            self.cmd_height = self.target_height
            self.publish_cmd()
            
            if self.is_moving:
                if not self.returning_home:
                    # 목표(up/down) 도달 완료 -> 다시 홈(0.5)으로 복귀 시작
                    self.node.get_logger().info(f'[{self.robot_name}] Reached target. Returning home...')
                    self.target_height = self.home_height
                    self.returning_home = True
                else:
                    # 홈 복귀 완료
                    self.is_moving = False
                    self.returning_home = False
                    self.node.get_logger().info(f'[{self.robot_name}] Action complete.')
            return

        # 목표 방향으로 이동
        if diff > 0: self.cmd_height += self.step_size
        else: self.cmd_height -= self.step_size
        self.publish_height(self.cmd_height)

    def publish_height(self, height):
        traj = JointTrajectory()
        traj.header.stamp.sec = 0
        traj.header.stamp.nanosec = 0
        traj.header.frame_id = 'world'
        traj.joint_names = [self.joint_name]
        
        point = JointTrajectoryPoint()
        point.positions = [height]
        point.time_from_start = Duration(sec=0, nanosec=20000000)
        
        traj.points = [point]
        self.pub.publish(traj)
        
    def publish_cmd(self):
        self.publish_height(self.cmd_height)

class MultiArmActionController(Node):
    def __init__(self):
        super().__init__('multi_arm_action_controller')
        
        # ID와 네임스페이스 매핑
        self.id_map = {
            "blue": "robot1",
            "white": "robot2"
        }
        
        self.robots = {}
        for robot_id, name in self.id_map.items():
            pub = self.create_publisher(JointTrajectory, f'/{name}/joint_trajectory', 10)
            joint_name = f'simple_gripper::palm_riser'
            
            handler = RobotActionHandler(self, name, joint_name, pub)
            self.robots[robot_id] = handler
            
            # 구독자 설정
            self.create_subscription(JointState, f'/{name}/joint_states', 
                                    partial(self.joint_state_callback, robot_id=robot_id), 10)

        # JSON 명령을 받을 토픽 (String 타입으로 JSON 전달 가정)
        self.command_sub = self.create_subscription(String, 'game_commands', self.json_command_callback, 10)
        
        self.timer = self.create_timer(0.02, self.control_loop)
        self.get_logger().info('Game Controller Ready. Send JSON to /game_commands')

    def joint_state_callback(self, msg, robot_id):
        handler = self.robots[robot_id]
        if handler.joint_name in msg.name:
            idx = msg.name.index(handler.joint_name)
            handler.update_current_height(msg.position[idx])

    def json_command_callback(self, msg):
        try:
            commands = json.loads(msg.data)
            for cmd in commands:
                robot_id = cmd.get('id')
                action = cmd.get('action')
                if robot_id in self.robots:
                    self.robots[robot_id].start_action(action)
        except Exception as e:
            self.get_logger().error(f'Failed to parse JSON: {e}')

    def control_loop(self):
        for handler in self.robots.values():
            handler.step()

def main(args=None):
    rclpy.init(args=args)
    node = MultiArmActionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
