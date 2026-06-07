# llm_processor.py
import json
from openai import OpenAI
from config import OPENAI_API_KEY

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """당신은 '청기백기' 게임 명령어를 파싱하는 전문 JSON 변환기입니다.

[STT 오인식 보정 규칙]
음성 인식 오류로 인해 잘못 입력된 단어를 문맥에 맞게 반드시 보정한 후 파싱하세요.

- 청기(blue)로 보정해야 하는 단어(예시):
  "전기", "청기", "청이", "정기", "천기", "청기야", "칭기", "첫기", "쳥기", "청", "파란기", "파란", "파랑기"

- 백기(white)로 보정해야 하는 단어(예시):
  "백기", "밖에", "밖기", "바기", "백이", "뱅기", "백", "하얀기", "하얀", "하양기", "희기", "흰기"

- 올려(up)로 보정해야 하는 단어(예시):
  "올려", "올려요", "올리고", "올리어", "올려라", "올라", "들어", "위로", "위에"

- 내려(down)로 보정해야 하는 단어(예시):
  "내려", "내려요", "내리고", "내리어", "내려라", "내려봐", "아래로", "아래에"

- 흔들어(shake)로 보정해야 하는 단어(예시):
  "흔들어", "흔들어요", "흔들고", "흔들어라", "흔들기", "흔들다", "흔들흔들", "흔들어봐"

- 보정 예시:
  "전기 올리고 밖에 내려" → 청기 올리고 백기 내려
  "칭기 올려 뱅기 내려" → 청기 올려 백기 내려
  "파란 들어 하얀 아래로" → 청기 올려 백기 내려
  "청기 흔들어 백기 내려" → 청기 흔들어 백기 내려

[파싱 규칙]
1. 반드시 아래 JSON 구조로만 응답하세요.
2. "commands" 배열에 명령을 **말해진 순서대로** 나열하세요.
3. "id" 값: "blue"(청기), "white"(백기)
4. "action" 값: "up"(올려), "down"(내려), "shake"(흔들어)
5. "모두"가 나오면 "blue"와 "white" 두 객체를 **이 순서대로** 각각 추가하세요.
6. '그리고', '다음에', '~하고' 같은 접속어는 무시하고 행동만 추출하세요.
7. 같은 기(旗)가 연속으로 다른 동작이면 각각 별도 객체로 추가하세요.

[응답 형식 예시]
입력: "청기 올리고 백기 내려 백기 흔들어"
출력:
{
  "commands": [
    {"id": "blue",  "action": "up"},
    {"id": "white", "action": "down"}
    {"id": "white", "action": "shake"}
  ]
}

입력: "청기 올리고 백기 내려 백기 올리고 청기 흔들어"
출력:
{
  "commands": [
    {"id": "blue",  "action": "up"},
    {"id": "white", "action": "down"},
    {"id": "white", "action": "up"},
    {"id": "blue",  "action": "shake"}
  ]
}

입력: "모두 올려"
출력:
{
  "commands": [
    {"id": "blue",  "action": "up"},
    {"id": "white", "action": "up"}
  ]
}
입력: "모두 흔들어"
출력:
{
  "commands": [
    {"id": "blue",  "action": "shake"},
    {"id": "white", "action": "shake"}
  ]
}

JSON 외의 텍스트는 절대 출력하지 마세요."""


def process_text_to_commands(text: str) -> list[dict]:
    """
    STT로 인식된 텍스트를 LLM에 보내 순서가 보장된 명령 배열로 변환합니다.

    Returns:
        [{"id": "blue"|"white", "action": "up"|"down"}, ...] 형태의 리스트.
        오류 발생 시 빈 리스트 반환.
    """
    user_prompt = f'입력: "{text}"\n출력:'

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,  # 결정론적 출력
        )

        raw_result = response.choices[0].message.content
        parsed = json.loads(raw_result.strip())
        commands = parsed.get("commands", [])

        # 기본 유효성 검사
        valid_ids      = {"blue", "white"}
        valid_actions  = {"up", "down", "shake"}
        validated = [
            cmd for cmd in commands
            if cmd.get("id") in valid_ids and cmd.get("action") in valid_actions
        ]

        if len(validated) != len(commands):
            print(f"⚠️ [LLM] 일부 명령이 유효하지 않아 제거되었습니다. (원본 {len(commands)}개 → 유효 {len(validated)}개)")

        return validated

    except json.JSONDecodeError:
        print(f"⚠️ [LLM 파싱 에러] JSON 형식이 아닙니다.")
        return []
    except Exception as e:
        print(f"⚠️ [OpenAI 호출 에러] {e}")
        return []


def commands_to_steps(commands: list[dict]) -> list[dict]:
    """
    순차 명령 배열을 '동작 스텝' 단위로 묶습니다.

    같은 스텝 안에 blue 와 white 가 함께 있으면 동시 동작,
    단독이면 단일 동작입니다.

    Args:
        commands: process_text_to_commands() 의 반환값

    Returns:
        [{"blue": "up"}, {"white": "down", "blue": "up"}, ...] 형태의 스텝 리스트
    """
    steps = []
    current: dict = {}

    for cmd in commands:
        flag_id = cmd.get("id")
        action  = cmd.get("action")
        if not flag_id or not action:
            continue

        # 이미 현재 스텝에 같은 기(旗)가 있으면 새 스텝 시작
        if flag_id in current:
            steps.append(current)
            current = {}

        current[flag_id] = action

    if current:
        steps.append(current)

    return steps