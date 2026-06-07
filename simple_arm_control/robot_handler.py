# robot_handler.py
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState
from builtin_interfaces.msg import Duration
from . import action_flag

class RobotHandlerNode(Node):
    def __init__(self):
        super().__init__('robot_handler_node')
        
        # 파라미터로 로봇 이름과 ID를 받음 (실행 시 설정 가능)
        self.declare_parameter('robot_name', 'robot1')
        self.declare_parameter('robot_id', 'blue')
        self.robot_name = self.get_parameter('robot_name').value
        self.robot_id = self.get_parameter('robot_id').value

        # 토픽 설정
        self.pub_traj = self.create_publisher(JointTrajectory, f'/{self.robot_name}/joint_trajectory', 10)
        self.pub_status = self.create_publisher(String, f'/{self.robot_name}/status', 10)
        
        self.sub_goal = self.create_subscription(String, f'/{self.robot_name}/goal', self.goal_callback, 10)
        self.sub_js = self.create_subscription(JointState, f'/{self.robot_name}/joint_states', self.js_callback, 10)

        # 상태 변수
        self.current_height = 0.5
        self.current_roll = 0.0
        self.target_val = 0.5
        self.is_busy = False
        self.initialized = False
        self.task_sequence = []
        self.current_task_type = None # 'height' or 'roll'
        
        self.epsilon = 0.03
        self.actual_riser_name = None
        self.actual_roll_name = None

        # 상태 보고 타이머
        self.create_timer(0.1, self.report_status)
        # 제어 루프 타이머
        self.create_timer(0.02, self.control_loop)

        self.get_logger().info(f'[{self.robot_name}] Handler Node Started for ID: {self.robot_id}')

    def report_status(self):
        msg = String()
        msg.data = "BUSY" if self.is_busy else "IDLE"
        self.pub_status.publish(msg)

    def js_callback(self, msg):
        if self.actual_riser_name is None:
            for n in msg.name:
                if 'palm_riser' in n: self.actual_riser_name = n
                if 'arm_wrist_roll_joint' in n: self.actual_roll_name = n
        
        if self.actual_riser_name in msg.name:
            self.current_height = msg.position[msg.name.index(self.actual_riser_name)]
            self.initialized = True
        if self.actual_roll_name in msg.name:
            self.current_roll = msg.position[msg.name.index(self.actual_roll_name)]

    def goal_callback(self, msg):
        if self.is_busy:
            self.get_logger().warn(f'[{self.robot_name}] Ignored: Still busy with previous action.')
            return
        
        action_type = msg.data
        sequence = action_flag.get_action_sequence(action_type)
        task_type = 'roll' if action_type == 'shake' else 'height'
        
        self.task_sequence = list(sequence)
        self.current_task_type = task_type
        self.target_val = self.task_sequence.pop(0) # 첫 번째 목표 설정
        self.is_busy = True
        
        # ⚠️ 명령 받자마자 즉시 BUSY 상태 발행 (Brain 노드 동기화)
        self.report_status()
        self.get_logger().info(f'[{self.robot_name}] New Action Started: {action_type} (First target: {self.target_val})')

    def control_loop(self):
        if not self.initialized or not self.is_busy: return

        # 현재 작업의 목표 도달 확인
        curr = self.current_height if self.current_task_type == 'height' else self.current_roll
        if abs(self.target_val - curr) < self.epsilon:
            if self.task_sequence:
                # 다음 단계로 진행
                self.target_val = self.task_sequence.pop(0)
                self.get_logger().info(f'[{self.robot_name}] Next step: {self.target_val}')
            else:
                # 모든 시퀀스 완료
                self.get_logger().info(f'[{self.robot_name}] Action Completed.')
                self.is_busy = False
                self.report_status() # 즉시 IDLE 보고
                return

        # 트래젝토리 발행
        self.publish_traj()

    def publish_traj(self):
        traj = JointTrajectory()
        traj.header.stamp.sec = 0
        traj.header.stamp.nanosec = 0
        
        h_val = self.target_val if self.current_task_type == 'height' else self.current_height
        r_val = self.target_val if self.current_task_type == 'roll' else self.current_roll
        
        names = []; pos = []
        if self.actual_riser_name: names.append(self.actual_riser_name); pos.append(h_val)
        if self.actual_roll_name: names.append(self.actual_roll_name); pos.append(r_val)
        
        traj.joint_names = names
        p = JointTrajectoryPoint()
        p.positions = pos
        p.time_from_start = Duration(sec=0, nanosec=50000000)
        traj.points = [p]
        self.pub_traj.publish(traj)

def main(args=None):
    rclpy.init(args=args)
    node = RobotHandlerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
