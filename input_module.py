"""
input_module.py
인포 브릿지 - 입력 처리 모듈

역할:
1. 로터리 엔코더 회전(A, B) 감지 -> 언어 선택 변경
2. 엔코더 클릭 버튼(S1) 감지 -> 촬영 트리거

배선 (사용자 확인 기준):
    엔코더 C(공통, 위쪽 3핀 중 가운데) -> 라즈베리파이 GND
    엔코더 A                         -> GPIO 27
    엔코더 B                         -> GPIO 22
    엔코더 S1(버튼)                   -> GPIO 17
    엔코더 S2(버튼)                   -> 라즈베리파이 GND

사용 전 설치 필요:
    pip install gpiozero
"""

from gpiozero import Button, DigitalInputDevice

# ---- 설정값 (실제 배선한 GPIO 번호) ----
ENCODER_PIN_A = 27
ENCODER_PIN_B = 22
BUTTON_PIN = 17

# 로터리 엔코더로 선택할 수 있는 언어 목록
# ai_module.py의 LANGUAGE_NAMES 키와 맞춰야 함
LANGUAGES = ["ko", "en", "ja", "zh"]
LANGUAGE_LABELS = {
    "ko": "한국어",
    "en": "English",
    "ja": "日本語",
    "zh": "中文",
}

# 현재 선택된 언어의 인덱스 (전역 상태)
_current_language_index = 0


def get_current_language() -> str:
    """현재 선택된 언어 코드를 반환 (예: 'ko')"""
    return LANGUAGES[_current_language_index]


def get_current_language_label() -> str:
    """현재 선택된 언어의 사람이 읽는 이름을 반환 (예: '한국어')"""
    return LANGUAGE_LABELS[get_current_language()]


class RotaryEncoder:
    """
    2상(A, B) 로터리 엔코더의 회전 방향을 감지하는 클래스.
    A핀이 먼저 떨어지면 시계방향(CW), B핀이 먼저 떨어지면 반시계방향(CCW)으로 판별.
    """

    def __init__(self, pin_a: int, pin_b: int, on_clockwise=None, on_counterclockwise=None):
        self._on_clockwise = on_clockwise
        self._on_counterclockwise = on_counterclockwise

        # pull_up=True: 평소 HIGH, 눌리거나 접점이 붙으면 LOW로 떨어짐
        self._input_a = DigitalInputDevice(pin_a, pull_up=True)
        self._input_b = DigitalInputDevice(pin_b, pull_up=True)

        self._last_state = (self._input_a.value << 1) | self._input_b.value
        self._step_count = 0

        # 두 핀의 모든 상태 변화를 읽어 빠른 회전에서도 단계를 놓치지 않는다.
        self._input_a.when_activated = self._decode_rotation
        self._input_a.when_deactivated = self._decode_rotation
        self._input_b.when_activated = self._decode_rotation
        self._input_b.when_deactivated = self._decode_rotation

    def _decode_rotation(self):
        state = (self._input_a.value << 1) | self._input_b.value
        transition = (self._last_state << 2) | state
        direction = {
            0b0001: 1, 0b0111: 1, 0b1110: 1, 0b1000: 1,
            0b0010: -1, 0b1011: -1, 0b1101: -1, 0b0100: -1,
        }.get(transition, 0)
        self._step_count += direction
        self._last_state = state

        # 일반 엔코더 한 칸은 4개의 유효 전이로 구성된다.
        if abs(self._step_count) >= 4:
            if self._step_count > 0 and self._on_clockwise:
                self._on_clockwise()
            elif self._step_count < 0 and self._on_counterclockwise:
                self._on_counterclockwise()
            self._step_count = 0


def _handle_clockwise():
    """다이얼을 오른쪽(시계방향)으로 돌렸을 때: 다음 언어로 이동"""
    global _current_language_index
    _current_language_index = (_current_language_index + 1) % len(LANGUAGES)
    print(f"[입력 모듈] 언어 선택 -> {get_current_language_label()}")


def _handle_counterclockwise():
    """다이얼을 왼쪽(반시계방향)으로 돌렸을 때: 이전 언어로 이동"""
    global _current_language_index
    _current_language_index = (_current_language_index - 1) % len(LANGUAGES)
    print(f"[입력 모듈] 언어 선택 -> {get_current_language_label()}")


def setup_input_handlers(on_button_pressed):
    """
    엔코더 회전(언어 선택) + 버튼(촬영 트리거) 핸들러를 등록한다.

    Args:
        on_button_pressed: 버튼을 눌렀을 때 실행할 콜백 함수 (main.py에서 전달)

    Returns:
        (encoder, button) 객체. 프로그램이 끝날 때까지 참조를 유지해야 콜백이 계속 동작함.
    """
    encoder = RotaryEncoder(
        ENCODER_PIN_A,
        ENCODER_PIN_B,
        on_clockwise=_handle_clockwise,
        on_counterclockwise=_handle_counterclockwise,
    )

    button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.2)
    button.when_pressed = on_button_pressed

    print(f"[입력 모듈] 준비 완료. 현재 언어: {get_current_language_label()}")
    return encoder, button


if __name__ == "__main__":
    # 단독 테스트: 다이얼 돌리면 언어가 바뀌고, 버튼 누르면 메시지 출력
    from signal import pause

    def _test_button_pressed():
        print(f"[테스트] 버튼 눌림! 현재 언어: {get_current_language_label()}")

    setup_input_handlers(_test_button_pressed)
    print("[테스트] 다이얼을 돌리거나 버튼을 눌러보세요. 종료: Ctrl+C")
    pause()
