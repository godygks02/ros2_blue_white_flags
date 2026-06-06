"""
로봇의 개별 동작(Action)들을 정의하는 모듈입니다.
새로운 동작이 필요할 경우 여기에 함수를 추가하면 됩니다.
"""

def get_action_target(action_type):
    """
    동작 타입에 따른 목표 높이를 반환합니다.
    """
    targets = {
        "up": 0.9,
        "down": 0.1,
        "home": 0.5,
        "ready": 0.5,
        "rotate": 3.14
    }
    return targets.get(action_type, 0.5)

def get_action_sequence(action_type):
    """
    나중에 복잡한 연속 동작이 필요할 경우를 대비한 함수 예시입니다.
    현재는 단일 목표값만 반환합니다.
    """
    if action_type == "up":
        return [0.9, 0.5]  # 0.9로 갔다가 다시 0.5로 돌아옴
    elif action_type == "down":
        return [0.1, 0.5]
    else:
        return [0.5]
