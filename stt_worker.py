# stt_worker.py
import io
import time
import threading
import speech_recognition as sr
from pynput import keyboard

def continuous_listen(command_queue, stop_event):
    """
    Push-to-Talk 방식의 음성 인식 워커.
    - 스페이스바를 누르고 있는 동안 마이크 입력을 지속적으로 녹음
    - 스페이스바를 떼는 순간 녹음을 중단하고 Google STT로 전송
    - 인식된 텍스트를 command_queue에 넣어 LLM 처리를 트리거함
    """
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.energy_threshold = 300

    try:
        mic = sr.Microphone()
    except Exception as e:
        print(f"⚠️ [STT] 마이크 연결 실패: {e}")
        return

    # 주변 소음 적응
    with mic:
        print("\n[STT] 🎙️ 주변 소음 적응 중 (2초간)...")
        recognizer.adjust_for_ambient_noise(mic, duration=2)

    print("\n[STT] 🟢 준비 완료! [스페이스바]를 누르고 있는 동안 말씀하세요. (종료: Ctrl+C)")
    print("       ▶ 누르는 동안 계속 녹음 → 떼는 순간 인식 시작\n")

    # ---------- 상태 변수 ----------
    is_recording = False       # 현재 녹음 중 여부
    recording_lock = threading.Lock()

    # ---------- 오디오 청크를 쌓을 버퍼 ----------
    audio_frames = []
    sample_rate = None
    sample_width = None

    # ---------- 녹음 스레드 ----------
    record_stop_event = threading.Event()

    def recording_thread_fn():
        """스페이스바가 눌려 있는 동안 오디오 청크를 지속적으로 수집한다."""
        nonlocal audio_frames, sample_rate, sample_width

        with mic as source:
            sr_source = source  # AudioSource 객체
            sample_rate = source.SAMPLE_RATE
            sample_width = source.SAMPLE_WIDTH

            print("🔴 [녹음 시작] 말씀하세요...")
            while not record_stop_event.is_set():
                # chunk_size 만큼 raw PCM 데이터를 읽어 버퍼에 추가
                buffer = sr_source.stream.read(sr_source.CHUNK)
                audio_frames.append(buffer)

        print("⏹️  [녹음 완료] 인식 중...")

    record_thread = None

    # ---------- 키보드 이벤트 ----------
    def on_press(key):
        nonlocal is_recording, audio_frames, sample_rate, sample_width, record_thread

        if key == keyboard.Key.space:
            with recording_lock:
                if not is_recording:
                    is_recording = True
                    audio_frames = []       # 버퍼 초기화
                    sample_rate = None
                    sample_width = None
                    record_stop_event.clear()

                    record_thread = threading.Thread(
                        target=recording_thread_fn, daemon=True
                    )
                    record_thread.start()

    def on_release(key):
        nonlocal is_recording, record_thread

        if key == keyboard.Key.space:
            with recording_lock:
                if is_recording:
                    is_recording = False
                    record_stop_event.set()         # 녹음 스레드 종료 신호

                    # 녹음 스레드가 완전히 끝날 때까지 대기 (최대 2초)
                    if record_thread:
                        record_thread.join(timeout=2)
                        record_thread = None

                    # 수집된 프레임이 있으면 STT 처리
                    if audio_frames and sample_rate and sample_width:
                        _process_audio(audio_frames, sample_rate, sample_width)
                    else:
                        print("⚠️ [STT] 녹음된 오디오가 없습니다.")

    def _process_audio(frames, rate, width):
        """수집된 PCM 프레임을 합쳐 Google STT에 보낸다."""
        raw_data = b"".join(frames)
        audio_data = sr.AudioData(raw_data, rate, width)

        try:
            text = recognizer.recognize_google(audio_data, language="ko-KR")
            if text.strip():
                print(f"✅ [STT 인식됨]: '{text.strip()}'")
                command_queue.put(text.strip())
            else:
                print("⚠️ [STT] 빈 텍스트가 반환되었습니다.")
        except sr.UnknownValueError:
            print("⚠️ [STT] 음성을 알아듣지 못했습니다. 더 명확하게 말씀해 주세요.")
        except sr.RequestError as e:
            print(f"⚠️ [STT] Google 서버 오류: {e}")
        except Exception as e:
            print(f"⚠️ [STT 처리 에러] {e}")

        print("\n[STT] 🟢 다음 명령을 위해 [스페이스바]를 누르고 말씀하세요.\n")

    # 키보드 리스너 시작
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    # 메인 루프: stop_event 신호가 올 때까지 대기
    while not stop_event.is_set():
        time.sleep(0.05)

    listener.stop()