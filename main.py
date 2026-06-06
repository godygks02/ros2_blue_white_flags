# main.py
import threading
import queue
import time
from stt_worker import continuous_listen
from llm_processor import process_text_to_commands

def main():
    print("=== 🤖 청기백기 게임 파이프라인 (OpenAI + 스페이스바 모드) ===")

    command_queue = queue.Queue()
    stop_event = threading.Event()

    stt_thread = threading.Thread(
        target=continuous_listen, 
        args=(command_queue, stop_event), 
        daemon=True
    )
    stt_thread.start()

    try:
        while True:
            if not command_queue.empty():
                raw_text = command_queue.get()
                print(f"\n🧠 [OpenAI 처리 중] 입력 텍스트: '{raw_text}'")
                
                commands_list = process_text_to_commands(raw_text)
                
                if not commands_list:
                    continue

                # 묶음 vs 단일/연속 분리 알고리즘
                steps = []
                current_step = {}
                
                for cmd in commands_list:
                    flag_id = cmd.get("id")
                    action = cmd.get("action")
                    
                    if not flag_id or not action:
                        continue
                        
                    if flag_id in current_step:
                        steps.append(current_step)
                        current_step = {}
                        
                    current_step[flag_id] = action
                    
                if current_step:
                    steps.append(current_step)

                # 로봇 제어 신호 출력부
                for idx, step in enumerate(steps):
                    print(f"▶️ [동작 스텝 {idx+1}]")
                    
                    if len(step) == 2:
                        print(f"  👉 [묶음 전송] 청기: {step.get('blue')}, 백기: {step.get('white')} (동시 동작)")
                    else:
                        flag_name = "청기" if "blue" in step else "백기"
                        action_val = list(step.values())[0]
                        print(f"  👉 [단일 전송] {flag_name}: {action_val}")

                    time.sleep(1) 
                    
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n🛑 [시스템] 종료 신호를 받았습니다. 스레드를 정리합니다...")
        stop_event.set()
        stt_thread.join(timeout=2)
        print("✅ 프로그램이 안전하게 종료되었습니다.")

if __name__ == "__main__":
    main()