import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from builtin_interfaces.msg import Duration
from functools import partial

class MultiArmController(Node):
    def __init__(self):
        super().__init__('multi_arm_controller')
        
        self.robot_names = ['robot1', 'robot2']
        self.robots = {}
        
        for name in self.robot_names:
            self.robots[name] = {
                'pub': self.create_publisher(JointTrajectory, f'/{name}/joint_trajectory', 10),
                'target': 0.0,
                'current': 0.0,
                'cmd': 0.0,
                'moving': False,
                'initialized': False,
                # 찾고자 하는 관절의 키워드
                'joint_keyword': 'palm_riser',
                'actual_joint_name': None 
            }
            
            # 각 로봇별 토픽 구독
            self.create_subscription(JointState, f'/{name}/joint_states', 
                                    partial(self.joint_state_callback, robot_name=name), 10)
            self.create_subscription(Float64, f'/{name}/arm_height', 
                                    partial(self.height_callback, robot_name=name), 10)

        self.step_size = 0.05
        self.delay = 0.02
        self.timer = self.create_timer(self.delay, self.move_step_callback)
        self.get_logger().info('Multi-Arm Controller Initialized with Auto-Naming.')

    def joint_state_callback(self, msg, robot_name):
        robot = self.robots[robot_name]
        
        # 실제 관절 이름 자동 찾기 (최초 1회)
        if robot['actual_joint_name'] is None:
            for name in msg.name:
                if robot['joint_keyword'] in name:
                    robot['actual_joint_name'] = name
                    self.get_logger().info(f'[{robot_name}] Found Joint: {name}')
                    break
        
        if robot['actual_joint_name'] in msg.name:
            idx = msg.name.index(robot['actual_joint_name'])
            robot['current'] = msg.position[idx]
            if not robot['initialized']:
                robot['cmd'] = robot['current']
                # 시작 시 초기 목표 위치를 0.5로 설정
                robot['target'] = 0.5 
                robot['moving'] = True
                robot['initialized'] = True
                self.get_logger().info(f'[{robot_name}] Initialized. Moving to start position: 0.5')

    def height_callback(self, msg, robot_name):
        robot = self.robots[robot_name]
        robot['target'] = msg.data
        robot['moving'] = True
        self.get_logger().info(f'[{robot_name}] Target set to: {robot["target"]:.2f}')

    def move_step_callback(self):
        for name, robot in self.robots.items():
            if not robot['initialized'] or robot['actual_joint_name'] is None:
                continue
            
            diff = robot['target'] - robot['cmd']
            if abs(diff) <= self.step_size:
                if robot['moving']:
                    robot['cmd'] = robot['target']
                    self.publish_height(name, robot['cmd'])
                    robot['moving'] = False
                    self.get_logger().info(f'[{name}] Target reached.')
                continue

            if diff > 0: robot['cmd'] += self.step_size
            else: robot['cmd'] -= self.step_size
            self.publish_height(name, robot['cmd'])

    def publish_height(self, robot_name, height):
        robot = self.robots[robot_name]
        traj = JointTrajectory()
        traj.header.stamp.sec = 0
        traj.header.stamp.nanosec = 0
        traj.header.frame_id = 'world'
        traj.joint_names = [robot['actual_joint_name']]
        
        point = JointTrajectoryPoint()
        point.positions = [height]
        point.time_from_start = Duration(sec=0, nanosec=20000000)
        
        traj.points = [point]
        robot['pub'].publish(traj)

def main(args=None):
    rclpy.init(args=args)
    node = MultiArmController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
