"""
로봇의 개별 동작(Action)들을 정의하는 모듈입니다.
"""

def get_action_target(action_type):
    """
    단일 동작 타입에 따른 목표값을 반환합니다.
    """
    targets = {
        "up": 0.9,
        "down": 0.1,
        "home": 0.5,
        "ready": 0.5,
        "shake": 0.0,
        "keep": 0.5
    }
    return targets.get(action_type, 0.5)

def get_action_sequence(action_type):
    """
    동작 타입에 따른 전체 이동 시퀀스(리스트)를 반환합니다.
    """
    if action_type == "up":
        return [0.9, 0.5]
    elif action_type == "down":
        return [0.1, 0.5]
    elif action_type == "shake":
        # 좌우로 흔들기 후 반드시 0.0으로 복귀
        return [0.8, -0.8, 0.8, -0.8, 0.0]
    elif action_type == "home" or action_type == "ready":
        return [0.5]
    else:
        return [0.5]
