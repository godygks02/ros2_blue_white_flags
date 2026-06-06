# ROS 2 Blue White Flags Game

Gazebo 시뮬레이터에서 로봇 팔(`simple_arm_gripper`)을 제어하여 청기백기 게임을 구현하기 위한 ROS 2 패키지입니다.

## 주요 기능
- 중력 및 물리 설정이 최적화된 로봇 팔 모델 포함
- 부드러운 애니메이션 효과가 적용된 관절 제어 노드 (`arm_controller`)
- 멀티 로봇(`robot1`, `robot2`) 독립 제어 지원

## 설치 및 사용 방법

### 1. 레포지토리 클론 및 모델 복사
팀원들은 이 패키지를 클론한 후, 포함된 `models` 폴더를 Gazebo 경로로 복사해야 합니다.
```bash
# 레포지토리 클론
cd ~/ros2_ws/src
git clone https://github.com/godygks02/ros2_blue_white_flags.git

# Gazebo 모델 복사
mkdir -p ~/.gazebo/models
cp -r ~/ros2_ws/src/ros2_blue_white_flags/models/* ~/.gazebo/models/
```

### 2. 패키지 빌드
```bash
cd ~/ros2_ws
colcon build --packages-select simple_arm_control
source install/setup.bash
```

### 3. 실행 순서

#### A. Gazebo 실행
```bash
ros2 launch gazebo_ros gazebo.launch.py
```

#### B. 로봇 소환 (Spawn)
터미널에서 각각 실행하여 두 대의 로봇을 소환합니다.
```bash
# 로봇 1
ros2 run gazebo_ros spawn_entity.py -file ~/.gazebo/models/simple_arm_gripper/model.sdf -entity robot1 -robot_namespace robot1 -x 0 -y 0

# 로봇 2
ros2 run gazebo_ros spawn_entity.py -file ~/.gazebo/models/simple_arm_gripper/model.sdf -entity robot2 -robot_namespace robot2 -x 0 -y 2
```

#### C. 제어 노드 실행
```bash
ros2 run simple_arm_control arm_controller
```

### 4. 제어 테스트
```bash
# robot1 높이 조절
ros2 topic pub --once /robot1/arm_height std_msgs/msg/Float64 "{data: 0.8}"

# robot2 높이 조절
ros2 topic pub --once /robot2/arm_height std_msgs/msg/Float64 "{data: 0.3}"
```
