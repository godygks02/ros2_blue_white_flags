# simple_arm_control: Blue White Flags Game (Distributed Control)

Gazebo 시뮬레이터에서 로봇 팔(`simple_arm_gripper`)을 제어하여 청기백기 게임을 수행하기 위한 ROS 2 패키지입니다. 
음성 인식(STT)과 LLM(GPT-4o-mini)을 결합하여 복잡한 순차적 명령을 안정적으로 수행할 수 있는 **분산 제어 아키텍처**를 채택하고 있습니다.

## 참여 조원
- 가천대학교 202135790 인공지능전공 신철민: 조장 (cm12066@gmail.com)
- 가천대학교 202135719 인공지능전공 김동찬 (kdch6686@gmail.com)
- 가천대학교 202135810 인공지능전공 이규석 (zxc201106@gmail.com)
- 가천대학교 202135768 인공지능전공 이유원 (ydbdnjs@gachon.ac.kr)
- 가천대학교 202135767 인공지능전공 박용우 (yongwoo5058@gmail.com)
- 가천대학교 202135845 인공지능전공 최준혁 (vosxja77@gachon.ac.kr)

---

## 🏗 시스템 아키텍처 (Architecture)

본 패키지는 명령의 생성부터 물리적 실행까지를 5개의 계층으로 분리하여 관리합니다.

1.  **Input Layer (`main.py`)**: 사용자 음성 녹음 및 텍스트 변환 (STT).
2.  **Intelligence Layer (`llm_processor.py`)**: 자연어를 분석하여 실행 가능한 JSON 명령 리스트로 변환 (LLM).
3.  **Distribution Layer (`arm_controller.py`)**: 생성된 명령들을 각 로봇(청기/백기)의 전용 채널로 배분.
4.  **Management Layer (`robot_handler.py`)**: 로봇별 독립적인 **Action Queue** 관리. 이전 동작 완료(Service Response) 확인 후 다음 명령 수행.
5.  **Execution Layer (`robot_servicer.py`)**: 실제 물리 엔진(Gazebo) 연동. **Step-by-step 이동**으로 속도를 조절하고 실시간 위치 피드백(JointState)을 통해 동작 완결성 보장.

---

## 📂 파일 및 노드 설명

### Core Nodes (ROS 2 Nodes)
*   **`arm_controller.py` (Multi-Arm Forwarder)**
    *   `game_commands` 토픽을 구독하여 `blue`/`white` 로봇에게 명령을 전달하는 중앙 배분기입니다.
*   **`robot_handler.py` (Sequential Queue Manager)**
    *   각 로봇당 하나씩 실행됩니다. 내부 큐를 가지고 있으며, ROS 2 서비스를 호출하여 동작을 수행합니다. 서비스 응답이 올 때까지 다음 명령을 보류하여 완벽한 순차 제어를 보장합니다.
*   **`robot_servicer.py` (Physical Service Server)**
    *   실제 로봇 관절을 제어하는 서비스 서버입니다. `/up`, `/down`, `/shake`, `/home` 서비스를 제공하며, 설정된 `step_size`에 따라 부드럽게 이동하고 물리적 목표 도달 시 응답을 반환합니다.

### Logic Files
*   **`main.py`**
    *   전체 시스템의 엔트리 포인트입니다. Push-to-Talk 방식의 음성 입력을 관리합니다.
*   **`action_flag.py`**
    *   로봇 동작의 세부 시퀀스(예: up -> [0.9m 상승, 0.5m 복귀])를 정의하는 설정 파일입니다.
*   **`llm_processor.py`**
    *   OpenAI API를 사용하여 자연어를 JSON 명령 배열로 변환하는 프롬프트 엔지니어링 로직이 담겨 있습니다.
*   **`stt_worker.py`**
    *   스레드 기반의 실시간 음성 녹음 및 Google STT 변환을 담당합니다.

---

## 🚀 실행 가이드 (Multi-Terminal Setup)

환경 설정을 완료한 후, 총 6개의 터미널에서 순차적으로 실행하는 것이 가장 안정적입니다.

### Step 0: 빌드 및 환경 설정
```bash
cd ~/ros2study
colcon build --packages-select simple_arm_control --symlink-install
source install/setup.bash
```

### Step 1: 물리 제어 서버 실행 (Servicers)
```bash
# 터미널 1 (청기 서버)
ros2 run simple_arm_control robot_servicer --ros-args -p robot_name:=robot1 -r __node:=robot1_servicer
# 터미널 2 (백기 서버)
ros2 run simple_arm_control robot_servicer --ros-args -p robot_name:=robot2 -r __node:=robot2_servicer
```

### Step 2: 순차 큐 관리자 실행 (Handlers)
```bash
# 터미널 3 (청기 핸들러)
ros2 run simple_arm_control robot_handler --ros-args -p robot_name:=robot1 -r __node:=robot1_handler
# 터미널 4 (백기 핸들러)
ros2 run simple_arm_control robot_handler --ros-args -p robot_name:=robot2 -r __node:=robot2_handler
```

### Step 3: 메인 시스템 실행
```bash
# 터미널 5 (중앙 배분기)
ros2 run simple_arm_control arm_controller
# 터미널 6 (음성 인식 메인)
cd ~/ros2study/src/simple_arm_control
python3 main.py
```

---

## 🎮 사용 방법
1.  모든 노드가 실행되면 로봇들이 자동으로 중앙(`0.5m`)으로 정렬됩니다.
2.  `main.py` 터미널에 포커스를 둔 상태에서 **[스페이스바]를 꾹 누르고** 말합니다.
    *   *예: "청기 올리고 백기 흔들어, 그 다음에 모두 내려"*
3.  스페이스바를 떼면 AI가 명령을 분석하고, 로봇들이 각자의 큐에 맞춰 **순차적으로** 동작을 수행합니다.

## 🛠 커스터마이징
*   **속도 조절**: `robot_servicer.py` 상단의 `self.step_size_h` (높이), `self.step_size_r` (회전) 값을 수정하세요.
*   **동작 간 딜레이**: `robot_handler.py`의 `self.wait_until` 관련 로직에서 시간을 조절할 수 있습니다 (기본 0.5초).
