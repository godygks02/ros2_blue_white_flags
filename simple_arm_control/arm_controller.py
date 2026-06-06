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
        
        self.riser_keyword = 'palm_riser'
        self.roll_keyword = 'arm_wrist_roll_joint'
        
        self.actual_riser_name = None
        self.actual_roll_name = None
        
        self.current_height = 0.5
        self.cmd_height = 0.5
        self.target_height = 0.5
        self.home_height = 0.5
        
        self.current_roll = 0.0
        self.cmd_roll = 0.0
        self.target_roll = 0.0
        
        self.step_size = 0.03
        self.roll_step_size = 0.1
        self.is_moving = False
        self.is_rotating = False
        self.returning_home = False
        self.initialized = False

    def handle_joint_state(self, msg):
        if self.actual_riser_name is None or self.actual_roll_name is None:
            for j_name in msg.name:
                if self.riser_keyword in j_name:
                    self.actual_riser_name = j_name
                if self.roll_keyword in j_name:
                    self.actual_roll_name = j_name
            
            if self.actual_riser_name:
                self.node.get_logger().info(f'[{self.name}] Matched Riser: {self.actual_riser_name}')
            if self.actual_roll_name:
                self.node.get_logger().info(f'[{self.name}] Matched Roll: {self.actual_roll_name}')
        
        if self.actual_riser_name and self.actual_riser_name in msg.name:
            idx = msg.name.index(self.actual_riser_name)
            self.current_height = msg.position[idx]
            if not self.initialized:
                self.cmd_height = self.current_height
                self.target_height = 0.5
                self.is_moving = True
                self.returning_home = True
                self.initialized = True
        
        if self.actual_roll_name and self.actual_roll_name in msg.name:
            idx = msg.name.index(self.actual_roll_name)
            self.current_roll = msg.position[idx]

    def start_action(self, action_type):
        if action_type == "rotate":
            self.target_roll = action_flag.get_action_target(action_type)
            self.is_rotating = True
            self.node.get_logger().info(f'[{self.name}] Action {action_type} -> {self.target_roll}')
        else:
            self.target_height = action_flag.get_action_target(action_type)
            self.is_moving = True
            self.returning_home = False
            self.node.get_logger().info(f'[{self.name}] Action {action_type} -> {self.target_height}')

    def step(self):
        if not self.initialized: return
        
        # Riser Step
        if self.actual_riser_name:
            diff = self.target_height - self.cmd_height
            if abs(diff) <= self.step_size:
                self.cmd_height = self.target_height
                if self.is_moving:
                    if not self.returning_home:
                        self.target_height = self.home_height
                        self.returning_home = True
                    else:
                        self.is_moving = False
            else:
                if diff > 0: self.cmd_height += self.step_size
                else: self.cmd_height -= self.step_size

        # Roll Step
        if self.actual_roll_name:
            diff_roll = self.target_roll - self.cmd_roll
            if abs(diff_roll) <= self.roll_step_size:
                self.cmd_roll = self.target_roll
                if self.is_rotating:
                    if self.target_roll != 0.0:
                        self.target_roll = 0.0 # Return to 0
                    else:
                        self.is_rotating = False
            else:
                if diff_roll > 0: self.cmd_roll += self.roll_step_size
                else: self.cmd_roll -= self.roll_step_size

        self.publish_trajectory()

    def publish_trajectory(self):
        traj = JointTrajectory()
        traj.header.stamp.sec = 0
        traj.header.stamp.nanosec = 0
        traj.header.frame_id = 'world'
        
        joint_names = []
        positions = []
        
        if self.actual_riser_name:
            joint_names.append(self.actual_riser_name)
            positions.append(self.cmd_height)
        if self.actual_roll_name:
            joint_names.append(self.actual_roll_name)
            positions.append(self.cmd_roll)
            
        traj.joint_names = joint_names
        p = JointTrajectoryPoint()
        p.positions = positions
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
