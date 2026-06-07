# Blue White Flags Game - Distributed ROS2 Control

Gazebo 시뮬레이터에서 로봇 팔(`simple_arm_gripper`)을 제어하여 청기백기 게임을 수행하기 위한 ROS 2 패키지입니다. 
음성 인식(STT)과 LLM(GPT-4o-mini)을 결합하여 복잡한 순차적 명령을 안정적으로 수행할 수 있는 **분산 제어 아키텍처**를 채택하고 있습니다.

## 참여 조원
- 가천대학교 202135790 인공지능전공 신철민: 조장 (cm12066@gmail.com)
- 가천대학교 202135719 인공지능전공 김동찬 (kdch6686@gmail.com)
- 가천대학교 202135810 인공지능전공 이규석 (zxc201106@gmail.com)
- 가천대학교 202135768 인공지능전공 이유원 (ydbdnjs@gachon.ac.kr)
- 가천대학교 202135767 인공지능전공 박용우 (yongwoo5058@gmail.com)
- 가천대학교 202135845 인공지능전공 최준혁 (vosxja77@gachon.ac.kr)


## 주요 기능
- **음성 인식 제어**: 사용자의 목소리를 텍스트로 변환하여 로봇을 움직입니다.
- **LLM 명령어 파싱**: "청기 올려", "백기 흔들어", "모두 내려" 등 복잡한 자연어 명령을 JSON 구조로 분석합니다.
- **다중 로봇 제어**: `blue` (robot1)와 `white` (robot2) 독립 및 동시 제어를 지원합니다.
- **동작 리스트**: 올리기(`up`), 내리기(`down`), 흔들기(돌리기)(`shake`)

## 설치 및 준비 사항

### 1. 의존성 패키지 설치
음성 인식 및 LLM 연동을 위해 다음 라이브러리가 필요합니다.
```bash
pip install openai SpeechRecognition pynput
```
*시스템에 `PortAudio` 라이브러리가 필요할 수 있습니다 (`sudo apt install python3-pyaudio` 혹은 `portaudio19-dev`).*

### 2. Gazebo 모델 복사
```bash
cd .../ros2_blue_white_flags
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
1.  모든 노드가 실행되면 로봇들이 자동으로 중앙으로 정렬됩니다.
2.  `main.py` 터미널에 포커스를 둔 상태에서 **[스페이스바]를 꾹 누르고** 말합니다.
    *   *예: "청기 올리고 백기 흔들어, 그 다음에 모두 내려"*
3.  스페이스바를 떼면 AI가 명령을 분석하고, 로봇들이 각자의 큐에 맞춰 **순차적으로** 동작을 수행합니다.

## 🛠 커스터마이징
*   **속도 조절**: `robot_servicer.py` 상단의 `self.step_size_h` (높이), `self.step_size_r` (회전) 값을 수정하세요.
*   **동작 간 딜레이**: `robot_handler.py`의 `self.wait_until` 관련 로직에서 시간을 조절할 수 있습니다 (기본 0.5초).

## Troubleshooting
1. 로봇 디자인 문제
- **문제**: 청기백기 게임에 적합한 로봇 디자인이 없어, 기존 로봇 모델만으로는 청기와 백기를 명확하게 표현하기 어려웠다.
- **해결 방안**: 게임 목적에 맞게 청기/백기를 표현할 수 있는 flag 모델을 추가하였다.
2. 음성 인식 처리 시간 문제
- **문제**: 음성 인식 및 자연어 명령 처리 과정에서 응답 시간이 길어지는 문제가 발생하였다.
- **해결 방안**: 성능을 최대한 보존하면서도 비교적 가벼운 모델인 GPT-4o-mini를 사용하여 명령 처리 시간을 줄였다.
3. 연속 입력으로 인한 동작 충돌 문제
- **문제**: 사용자가 명령을 연속으로 입력할 경우, 이전 동작이 완료되기 전에 다음 동작이 publish되어 로봇이 의도한 순서대로 움직이지 않는 문제가 발생하였다.
- **해결 방안**: 기존 topic 기반 단방향 publish 방식 대신 서비스 기반 양방향 통신으로 변경하였다. 이를 통해 이전 동작의 완료 여부를 확인한 뒤 다음 명령을 처리하도록 개선하였다.
4. 주변 노이즈 인식 문제
- **문제**: 음성 인식 과정에서 마이크가 사용자의 명령뿐만 아니라 주변 노이즈까지 인식하여 오작동 가능성이 있었다.
- **해결 방안**: 스페이스바를 누르고 있는 동안만 음성 인식이 활성화되도록 수정하였다. 이를 통해 사용자가 명령을 말하는 순간에만 입력을 처리하도록 하여 노이즈로 인한 오작동을 줄였다.
