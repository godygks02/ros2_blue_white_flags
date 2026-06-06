# llm_processor.py
import json
from openai import OpenAI
from config import OPENAI_API_KEY

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

def process_text_to_commands(text):
    """
    STT 텍스트를 [{"id":"blue","action":"up"}, ...] 형태의 JSON 배열로 반환합니다.
    """
    prompt = f"""
    당신은 청기백기 게임 명령어 파서입니다.
    사용자의 음성 인식 결과를 분석하여 아래 구조의 JSON 데이터로만 반환하세요.
    반드시 'commands'라는 키의 값으로 배열(List)을 넣어야 합니다.

    {{
        "commands": [
            {{"id": "blue", "action": "up"}},
            {{"id": "white", "action": "down"}}
        ]
    }}

    [동작 규칙]
    - "id" 값: "blue" (청기), "white" (백기)
    - "action" 값: "up" (올려), "down" (내려), "keep" (유지/가만히)
    - '모두'라는 말이 있으면 청기와 백기 객체를 각각 생성하세요.

    [실제 변환할 명령]
    입력: "{text}"
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output strictly JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}, # 순수 JSON 응답 강제
            temperature=0.0 # 무작위성 제거
        )
        
        raw_result = response.choices[0].message.content
        parsed_json = json.loads(raw_result.strip())
        
        # 딕셔너리 안에서 우리가 진짜 필요한 배열(List)만 뽑아서 반환
        return parsed_json.get("commands", [])
        
    except json.JSONDecodeError:
        print(f"⚠️ [LLM 파싱 에러] JSON 형식이 아닙니다. 원본: {raw_result}")
        return []
    except Exception as e:
        print(f"⚠️ [OpenAI 호출 에러] {e}")
        return []