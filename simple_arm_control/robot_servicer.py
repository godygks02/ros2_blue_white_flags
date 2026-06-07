# robot_servicer.py
import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Duration
from rclpy.callback_groups import ReentrantCallbackGroup
import time
from . import action_flag

class RobotServicer(Node):
    def __init__(self):
        super().__init__('robot_servicer')
        
        self.declare_parameter('robot_name', 'robot1')
        self.robot_name = self.get_parameter('robot_name').value

        # --- [속도 조절 변수] ---
        # 이 값을 수정하여 속도를 조절하세요.
        self.step_size_h = 0.04  # 높이 조절 속도 (클수록 빠름)
        self.step_size_r = 0.3  # 회전(흔들기) 속도 (클수록 빠름)
        # ----------------------

        self.riser_keyword = 'palm_riser'
        self.roll_keyword = 'arm_wrist_roll_joint'
        self.callback_group = ReentrantCallbackGroup()

        self.srv_up = self.create_service(Trigger, f'/{self.robot_name}/up', self.handle_up, callback_group=self.callback_group)
        self.srv_down = self.create_service(Trigger, f'/{self.robot_name}/down', self.handle_down, callback_group=self.callback_group)
        self.srv_shake = self.create_service(Trigger, f'/{self.robot_name}/shake', self.handle_shake, callback_group=self.callback_group)
        self.srv_home = self.create_service(Trigger, f'/{self.robot_name}/home', self.handle_home, callback_group=self.callback_group)

        self.pub_traj = self.create_publisher(JointTrajectory, f'/{self.robot_name}/joint_trajectory', 10)
        self.sub_js = self.create_subscription(
            JointState, f'/{self.robot_name}/joint_states', self.js_callback, 10,
            callback_group=self.callback_group
        )

        self.current_height = None
        self.current_roll = None
        
        # 현재 명령 중인 위치 (부드러운 이동을 위함)
        self.cmd_height = 0.5
        self.cmd_roll = 0.0
        
        self.actual_riser_name = None
        self.actual_roll_name = None
        self.epsilon = 0.04
        
        self.get_logger().info(f'[{self.robot_name}] Servicer with Speed Control Ready.')

    def js_callback(self, msg):
        if self.actual_riser_name is None or self.actual_roll_name is None:
            for n in msg.name:
                if n.endswith(self.riser_keyword): self.actual_riser_name = n
                if n.endswith(self.roll_keyword): self.actual_roll_name = n
        
        if self.actual_riser_name in msg.name:
            self.current_height = msg.position[msg.name.index(self.actual_riser_name)]
            if self.cmd_height is None: self.cmd_height = self.current_height
        if self.actual_roll_name in msg.name:
            self.current_roll = msg.position[msg.name.index(self.actual_roll_name)]
            if self.cmd_roll is None: self.cmd_roll = self.current_roll

    def handle_up(self, request, response): return self._execute_sequence("up", response)
    def handle_down(self, request, response): return self._execute_sequence("down", response)
    def handle_shake(self, request, response): return self._execute_sequence("shake", response)
    def handle_home(self, request, response): return self._execute_sequence("home", response)

    def _execute_sequence(self, action_type, response):
        # 초기화 대기
        wait_start = time.time()
        while (self.actual_riser_name is None or self.current_height is None) and rclpy.ok():
            if time.time() - wait_start > 5.0:
                response.success = False
                return response
            time.sleep(0.1)

        sequence = action_flag.get_action_sequence(action_type)
        is_roll = (action_type == "shake")
        
        # 동작 시작 전 현재 위치를 명령 시작점으로 동기화
        self.cmd_height = self.current_height
        self.cmd_roll = self.current_roll

        for target in sequence:
            while rclpy.ok():
                # 1. 단계별 목표치 계산 (Stepping)
                if is_roll:
                    diff = target - self.cmd_roll
                    if abs(diff) <= self.step_size_r:
                        self.cmd_roll = target
                    else:
                        self.cmd_roll += self.step_size_r if diff > 0 else -self.step_size_r
                else:
                    diff = target - self.cmd_height
                    if abs(diff) <= self.step_size_h:
                        self.cmd_height = target
                    else:
                        self.cmd_height += self.step_size_h if diff > 0 else -self.step_size_h

                # 2. 토픽 발행
                self._publish_cmd()

                # 3. 도달 확인 (명령치 도달 + 물리적 도달)
                phys_diff = abs(target - (self.current_roll if is_roll else self.current_height))
                if (is_roll and self.cmd_roll == target and phys_diff < self.epsilon) or \
                   (not is_roll and self.cmd_height == target and phys_diff < self.epsilon):
                    break
                
                time.sleep(0.04) # 25Hz 정도로 부드럽게 이동

        response.success = True
        return response

    def _publish_cmd(self):
        traj = JointTrajectory()
        traj.header.stamp.sec = 0
        traj.header.stamp.nanosec = 0
        traj.header.frame_id = 'world'
        
        names = []; pos = []
        if self.actual_riser_name:
            names.append(self.actual_riser_name); pos.append(self.cmd_height)
        if self.actual_roll_name:
            names.append(self.actual_roll_name); pos.append(self.cmd_roll)
            
        traj.joint_names = names
        p = JointTrajectoryPoint()
        p.positions = pos
        p.time_from_start = Duration(sec=0, nanosec=40000000)
        traj.points = [p]
        self.pub_traj.publish(traj)

def main(args=None):
    rclpy.init(args=args)
    node = RobotServicer()
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt: pass
    node.destroy_node()
    rclpy.shutdown()
