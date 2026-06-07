# main.py
import json
import threading
import queue

from stt_worker import continuous_listen
from llm_processor import process_text_to_commands


def main():
    print("=" * 55)
    print("  🤖 청기백기 Push-to-Talk 파이프라인")
    print("     ■ 스페이스바 누르고 있는 동안 말하기")
    print("     ■ 스페이스바 떼면 자동으로 인식 & 실행")
    print("     ■ 종료: Ctrl+C")
    print("=" * 55)

    command_queue = queue.Queue()
    stop_event    = threading.Event()

    stt_thread = threading.Thread(
        target=continuous_listen,
        args=(command_queue, stop_event),
        daemon=True,
    )
    stt_thread.start()

    try:
        while True:
            # 큐에서 STT 결과 텍스트 꺼내기
            try:
                raw_text = command_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            # LLM → 순차 명령 배열
            commands = process_text_to_commands(raw_text)
            if not commands:
                print("⚠️ 인식된 명령이 없습니다.")
                continue

            # JSON 배열 형태로 출력
            print(json.dumps(commands, ensure_ascii=False, indent=2))

    except KeyboardInterrupt:
        print("\n\n🛑 [시스템] 종료 신호. 스레드 정리 중...")
        stop_event.set()
        stt_thread.join(timeout=3)
        print("✅ 프로그램이 안전하게 종료되었습니다.")


if __name__ == "__main__":
    main()