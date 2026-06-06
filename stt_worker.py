# stt_worker.py
import speech_recognition as sr
from pynput import keyboard
import time

def continuous_listen(command_queue, stop_event):
    recognizer = sr.Recognizer()
    
    # [수정 1] 주변 소음 수준에 맞춰 인식 기준점(Threshold)을 실시간 자동 조정
    recognizer.dynamic_energy_threshold = True
    recognizer.energy_threshold = 300  # 기본값보다 약간 낮게 설정하여 작은 목소리도 잘 잡게 함

    # [수정 2] 마이크 장치 명시적 사용
    # 대부분의 환경에서는 default를 쓰지만, 오류 발생 시 0번 장치 고정
    try:
        source = sr.Microphone()
    except Exception as e:
        print(f"⚠️ [STT] 마이크 연결 실패: {e}")
        return

    space_pressed = False

    def on_press(key):
        nonlocal space_pressed
        if key == keyboard.Key.space:
            space_pressed = True

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    with source:
        print("\n[STT] 🎙️ 주변 소음 적응 중 (3초간)...")
        recognizer.adjust_for_ambient_noise(source, duration=3)
        
    print("\n[STT] 🟢 준비 완료! [스페이스바]를 한 번 누르면 음성을 듣습니다. (종료: Ctrl+C)")

    while not stop_event.is_set():
        if space_pressed:
            print("\n👂 [녹음 중...] 명령을 말씀하세요!")
            try:
                with source:
                    # [수정 3] 타임아웃을 5초로 늘리고, 더 잘 인식되도록 조치
                    audio_data = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                
                print("⏳ [녹음 완료] 변환 중...")
                # language='ko-KR'을 명시적으로 사용
                text = recognizer.recognize_google(audio_data, language='ko-KR')
                
                if text.strip():
                    print(f"✅ [STT 인식됨]: '{text.strip()}'")
                    command_queue.put(text.strip())
                    
            except sr.WaitTimeoutError:
                print("⚠️ [STT] 타임아웃: 너무 오래 기다렸습니다. 다시 시도하세요.")
            except sr.UnknownValueError:
                print("⚠️ [STT] 음성을 알아듣지 못했습니다. 조금 더 명확히 말씀해 주세요.")
            except Exception as e:
                print(f"⚠️ [STT 에러] {e}")
            
            print("▶️ 다시 명령하려면 [스페이스바]를 누르세요.")
            space_pressed = False
            
        time.sleep(0.05)

    listener.stop()