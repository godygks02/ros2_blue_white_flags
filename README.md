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
pip install -r requirements.txt
```
*시스템에 `PortAudio` 라이브러리가 필요할 수 있습니다 (`sudo apt install python3-pyaudio` 혹은 `portaudio19-dev`).*

### 2. 사전 준비 (빌드 및 모델 복사)
```bash
# 빌드
cd ~/ros2study
colcon build --packages-select simple_arm_control --symlink-install
source install/setup.bash

# 모델 파일 복사 (최초 1회)
mkdir -p ~/.gazebo/models
cp -r ~/ros2study/src/simple_arm_control/models/* ~/.gazebo/models/
```

---

## 🏗 시스템 아키텍처 (Architecture)

본 패키지는 명령의 생성부터 물리적 실행까지를 5개의 계층으로 분리하여 관리합니다.

1.  **Input Layer (`main.py`)**: 사용자 음성 녹음 및 텍스트 변환 (STT).
2.  **Intelligence Layer (`llm_processor.py`)**: 자연어를 분석하여 실행 가능한 JSON 명령 리스트로 변환 (LLM).
3.  **Distribution Layer (`arm_controller.py`)**: 생성된 명령들을 각 로봇(청기/백기)의 전용 채널로 배분.
4.  **Management Layer (`robot_handler.py`)**: 로봇별 독립적인 **Action Queue** 관리. 이전 동작 완료(Service Response) 확인 후 다음 명령 수행.
5.  **Execution Layer (`robot_servicer.py`)**: 실제 물리 엔진(Gazebo) 연동. **Step-by-step 이동**으로 속도를 조절하고 실시간 위치 피드백(JointState)을 통해 동작 완결성 보장.

<img width="3018" height="925" alt="rosgraph" src="https://github.com/user-attachments/assets/d0f87d1d-3f1e-4fb1-b2a6-3fec28cb67b9" />


---

## 📂 노드 상세 설명
*   **`arm_controller.py`**: `game_commands`를 받아 각 로봇 핸들러(`/robot1/goal`, `/robot2/goal`)로 전달합니다.
*   **`robot_handler.py`**: 명령 큐를 관리하며, 서비스 응답이 올 때까지 다음 작업을 보류하는 지휘관 노드입니다.
*   **`robot_servicer.py`**: 실제 관절 제어 및 물리적 도달 여부를 판단하여 응답을 주는 실행 노드입니다.

---

## 프롬프트 설계 구조

본 프로젝트의 프롬프트는 사용자의 음성 명령을 ROS 2 로봇 제어에 사용할 수 있는 JSON 명령으로 변환하기 위해 설계하였다. STT 결과에 오인식이 포함될 수 있으므로, LLM이 단어 보정과 명령 파싱을 함께 수행하도록 구성하였다.

### 1. 설계 목적

- 음성 명령을 로봇 제어용 JSON으로 변환
- STT 오인식 보정
- 청기/백기와 동작 명령 분리
- 명령 순서를 유지하여 순차 실행 가능하도록 구성

### 2. 입력 및 출력 구조

입력은 STT로 변환된 자연어 문장이다.

청기 올리고 백기 내려

출력은 `commands` 배열을 포함한 JSON 형식이다.

```python
{
  "commands": [
    {"id": "blue", "action": "up"},
    {"id": "white", "action": "down"}
  ]
}
```

### 3. 주요 프롬프트 규칙

- 청기 관련 단어는 `blue`로 변환
- 백기 관련 단어는 `white`로 변환
- "올려", "위로", "들어"는 `up`으로 변환
- "내려", "아래로"는 `down`으로 변환
- "흔들어"는 `shake`로 변환
- "모두"는 `blue`, `white` 두 명령으로 확장
- 명령은 사용자가 말한 순서대로 저장
- JSON 외의 문장은 출력하지 않도록 제한

### 4. 후처리 검증

LLM 응답 후 코드에서 한 번 더 유효성을 검사한다.

- 허용 ID: `blue`, `white`
- 허용 동작: `up`, `down`, `shake`

허용되지 않은 값은 제거하여 잘못된 로봇 명령이 실행되지 않도록 하였다.

### 5. 전체 흐름

음성 입력
-> STT 텍스트 변환
-> LLM 프롬프트 입력
-> 오인식 보정
-> JSON 명령 생성
-> 유효성 검사
-> ROS 2 명령 publish

### 6. 설계 특징

- 오인식에 강한 음성 명령 처리
- JSON 기반의 안정적인 로봇 명령 생성
- 순차 명령 실행을 고려한 구조
- ROS 2 제어 노드와 바로 연결 가능한 출력 형식

## 🚀 실행 가이드 (Full Setup Guide)

아래 순서대로 터미널을 각각 열어 실행해 주세요.

### Step 1: 시뮬레이션 환경 실행 (Gazebo & Spawn)
```bash
# 터미널 1: 가제보 실행
ros2 launch gazebo_ros gazebo.launch.py

# 터미널 2: 청기 로봇 (robot1) 소환
ros2 run gazebo_ros spawn_entity.py -file ~/.gazebo/models/simple_arm_blue_flag/model.sdf -entity robot1 -robot_namespace robot1 -x 0 -y 0

# 터미널 3: 백기 로봇 (robot2) 소환
ros2 run gazebo_ros spawn_entity.py -file ~/.gazebo/models/simple_arm_white_flag/model.sdf -entity robot2 -robot_namespace robot2 -x 0 -y 2
```

### Step 2: 물리 제어 서버 실행 (Servicers)
```bash
# 터미널 4 (청기 서버)
ros2 run simple_arm_control robot_servicer --ros-args -p robot_name:=robot1 -r __node:=robot1_servicer
# 터미널 5 (백기 서버)
ros2 run simple_arm_control robot_servicer --ros-args -p robot_name:=robot2 -r __node:=robot2_servicer
```

### Step 3: 순차 큐 관리자 실행 (Handlers)
```bash
# 터미널 6 (청기 핸들러)
ros2 run simple_arm_control robot_handler --ros-args -p robot_name:=robot1 -r __node:=robot1_handler
# 터미널 7 (백기 핸들러)
ros2 run simple_arm_control robot_handler --ros-args -p robot_name:=robot2 -r __node:=robot2_handler
```

### Step 4: 중앙 배분 및 음성 인식 실행
```bash
# 터미널 8 (중앙 배분기)
ros2 run simple_arm_control arm_controller
# 터미널 9 (음성 인식 메인)
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


