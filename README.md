# ROS 2 Blue White Flags Game (Voice & LLM Integrated)

Gazebo 시뮬레이터에서 로봇 팔(`simple_arm_gripper`)을 제어하여 청기백기 게임을 구현하기 위한 ROS 2 패키지입니다. 
최근 업데이트를 통해 **음성 인식(STT)**과 **LLM(GPT-4o-mini)**을 이용한 자연어 명령 제어 기능이 통합되었습니다.

## 참여 조원
- 가천대학교 202135790 인공지능전공 신철민: 조장 (cm12066@gmail.com)
- 가천대학교 202135719 인공지능전공 김동찬 (kdch6686@gmail.com)
- 가천대학교 202135810 인공지능전공 이규석 (zxc201106@gmail.com)
- 가천대학교 202135768 인공지능전공 이유원 (ydbdnjs@gachon.ac.kr)
- 가천대학교 202135767 인공지능전공 박용우 (yongwoo5058@gmail.com)
- 가천대학교 202135845 인공지능전공 최준혁 (vosxja77@gachon.ac.kr)


## 주요 기능
- **음성 인식 제어**: 사용자의 목소리를 텍스트로 변환하여 로봇을 움직입니다.
- **LLM 명령어 파싱**: "청기 올려", "백기 돌려", "모두 내려" 등 복잡한 자연어 명령을 JSON 구조로 분석합니다.
- **다중 로봇 제어**: `blue` (robot1)와 `white` (robot2) 독립 및 동시 제어를 지원합니다.
- **동작 리스트**: 올리기(`up`), 내리기(`down`), 흔들기(돌리기)(`rotate`), 유지

## 시스템 구조도
```mermaid
graph LR
    USER["🎤 사용자 음성 입력 (Voice)"]
    STT["stt_worker.py (음성 인식 스레드)"]
    MAIN["main.py (메인 파이프라인)"]
    LLM["llm_processor.py (GPT-4o-mini 파서)"]
    CONTROLLER["arm_controller (ROS 2 제어 노드)"]
    GAZEBO["🤖 Gazebo 시뮬레이터 (청기/백기 구동)"]

    USER --> STT
    STT --> MAIN
    MAIN --> LLM
    LLM --> MAIN
    MAIN --> CONTROLLER
    CONTROLLER --> GAZEBO

    USER -.->|Audio| STT
    STT -.->|ko-KR Text| MAIN
    MAIN -.->|Prompt Call| LLM
    LLM -.->|Strict JSON| MAIN
    MAIN -.->|/joint_trajectory| CONTROLLER
    CONTROLLER -.->|Joint Position| GAZEBO

    style USER fill:#E8F4F8,stroke:#3498DB,stroke-width:2px,color:#2980B9
    style STT fill:#F4F6F7,stroke:#7F8C8D,stroke-width:2px,color:#34495E
    style MAIN fill:#F4F6F7,stroke:#7F8C8D,stroke-width:2px,color:#34495E
    style LLM fill:#EBF5FB,stroke:#2980B9,stroke-width:2px,color:#1B4F72
    style CONTROLLER fill:#FEF9E7,stroke:#F39C12,stroke-width:2px,color:#7E5109
    style GAZEBO fill:#FEF9E7,stroke:#F39C12,stroke-width:2px,color:#7E5109
```

## 설치 및 준비 사항

### 1. 의존성 패키지 설치
음성 인식 및 LLM 연동을 위해 다음 라이브러리가 필요합니다.
```bash
pip install openai SpeechRecognition pynput
```
*시스템에 `PortAudio` 라이브러리가 필요할 수 있습니다 (`sudo apt install python3-pyaudio` 혹은 `portaudio19-dev`).*

### 2. Gazebo 모델 복사
```bash
# Gazebo 모델 경로에 모델 파일 복사
mkdir -p ~/.gazebo/models
cp -r .../ros2_blue_white_flags/models/* ~/.gazebo/models/
```

### 3. API 키 설정
패키지 루트 폴더의 `config.py.example` 파일을 열어 OpenAI API 키를 입력하고, 파일 확장자를 .py로 변경합니다.
```python
# config.py
OPENAI_API_KEY = "your-api-key-here"
```

## 실행 방법

### Step 1: Gazebo 시뮬레이션 실행
```bash
ros2 launch gazebo_ros gazebo.launch.py
```

### Step 2: 로봇 소환 (Spawn)
청기(robot1)와 백기(robot2) 모델을 소환합니다.
```bash
# 청기 로봇 (robot1)
ros2 run gazebo_ros spawn_entity.py -file ~/.gazebo/models/simple_arm_blue_flag/model.sdf -entity robot1 -robot_namespace robot1 -x 0 -y 0

# 백기 로봇 (robot2)
ros2 run gazebo_ros spawn_entity.py -file ~/.gazebo/models/simple_arm_white_flag/model.sdf -entity robot2 -robot_namespace robot2 -x 0 -y 2
```

### Step 3: 로봇 컨트롤러 노드 실행
로봇의 관절 제어 및 토픽 구독을 담당하는 메인 노드입니다.
```bash
# 새로운 터미널에서
source install/setup.bash
ros2 run simple_arm_control arm_controller
```

### Step 4: 음성 인식 파이프라인 실행
사용자의 목소리를 듣고 명령을 전달하는 노드입니다.
```bash
# 새로운 터미널에서
cd ~/ros2study/src/simple_arm_control
python3 main.py
```

## 사용 방법 (음성 제어)
1. `main.py`가 실행되면 **[스페이스바]**를 한 번 누릅니다.
2. "청기 올리고 백기 돌려" 또는 "모두 내려"라고 말씀하세요.
3. LLM이 명령을 분석하여 로봇이 동작을 수행합니다.
4. 다시 명령하려면 **[스페이스바]**를 다시 누릅니다.

## 참고 사항
- **돌리기 명령**: 그리퍼가 Z축 방향으로 180도 회전 후 다시 원위치로 돌아옵니다.
- **자동 복귀**: 청기백기 게임의 모든 동작(up/down/rotate)이 완료되면 로봇은 자동으로 중앙 위치(0.5 height / 0.0 roll)로 돌아오도록 설계되었습니다.
