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
    def __init__(self, node, robot_id, name, pub):
        self.node = node
        self.robot_id = robot_id
        self.name = name
        self.pub = pub
        
        self.target_keyword = 'palm_riser'
        self.actual_joint_name = None
        
        self.current_height = 0.5
        self.cmd_height = 0.5
        self.target_height = 0.5
        self.home_height = 0.5
        
        self.step_size = 0.03
        self.is_moving = False
        self.returning_home = False
        self.initialized = False

    def handle_joint_state(self, msg):
        if self.actual_joint_name is None:
            for j_name in msg.name:
                if self.target_keyword in j_name:
                    self.actual_joint_name = j_name
                    self.node.get_logger().info(f'[{self.name}] Matched: {j_name}')
                    break
        
        if self.actual_joint_name and self.actual_joint_name in msg.name:
            idx = msg.name.index(self.actual_joint_name)
            self.current_height = msg.position[idx]
            if not self.initialized:
                self.cmd_height = self.current_height
                self.target_height = 0.5
                self.is_moving = True
                self.returning_home = True
                self.initialized = True

    def start_action(self, action_type):
        # action_flag.py에서 목표 높이를 가져옴 (up: 0.9, down: 0.1)
        self.target_height = action_flag.get_action_target(action_type)
        self.is_moving = True
        self.returning_home = False
        self.node.get_logger().info(f'[{self.name}] Action {action_type} -> {self.target_height}')

    def step(self):
        if not self.initialized or self.actual_joint_name is None: return

        diff = self.target_height - self.cmd_height
        if abs(diff) <= self.step_size:
            self.cmd_height = self.target_height
            self.publish_height(self.cmd_height)
            
            if self.is_moving:
                if not self.returning_home:
                    # 목표 지점(0.9 or 0.1) 도착 -> 다시 0.5로 복귀
                    self.target_height = self.home_height
                    self.returning_home = True
                else:
                    # 복귀 완료
                    self.is_moving = False
            return

        if diff > 0: self.cmd_height += self.step_size
        else: self.cmd_height -= self.step_size
        self.publish_height(self.cmd_height)

    def publish_height(self, height):
        traj = JointTrajectory()
        traj.header.stamp.sec = 0
        traj.header.stamp.nanosec = 0
        traj.header.frame_id = 'world'
        traj.joint_names = [self.actual_joint_name]
        p = JointTrajectoryPoint()
        p.positions = [height]
        p.time_from_start = Duration(sec=0, nanosec=20000000)
        traj.points = [p]
        self.pub.publish(traj)

class MultiArmActionController(Node):
    def __init__(self):
        super().__init__('multi_arm_action_controller')
        
        self.id_map = {"blue": "robot1", "white": "robot2"}
        self.robots = {}
        
        for robot_id, name in self.id_map.items():
            pub = self.create_publisher(JointTrajectory, f'/{name}/joint_trajectory', 10)
            handler = RobotActionHandler(self, robot_id, name, pub)
            self.robots[robot_id] = handler
            
            self.create_subscription(JointState, f'/{name}/joint_states', 
                                    partial(self.joint_state_callback, robot_id=robot_id), 10)

        # [복구] JSON 명령 구독자 추가
        self.command_sub = self.create_subscription(String, 'game_commands', self.json_command_callback, 10)
        
        self.timer = self.create_timer(0.02, self.control_loop)
        self.get_logger().info('Multi-Arm Game Controller Ready.')

    def joint_state_callback(self, msg, robot_id):
        self.robots[robot_id].handle_joint_state(msg)

    def json_command_callback(self, msg):
        try:
            commands = json.loads(msg.data)
            for cmd in commands:
                r_id = cmd.get('id')
                action = cmd.get('action')
                if r_id in self.robots:
                    self.robots[r_id].start_action(action)
        except Exception as e:
            self.get_logger().error(f'JSON Error: {e}')

    def control_loop(self):
        for robot in self.robots.values():
            robot.step()

def main(args=None):
    rclpy.init(args=args)
    node = MultiArmActionController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
