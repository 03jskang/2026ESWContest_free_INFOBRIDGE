"""
input_module.py
인포 브릿지 - 입력 처리 모듈 (RPi.GPIO 버전)

역할:
1. 로터리 엔코더 회전(A, B) 감지 -> 언어 선택 변경
2. 엔코더 클릭 버튼(S1) 감지 -> 촬영 트리거

배선 (사용자 확인 기준):
    엔코더 C(공통, 위쪽 3핀 중 가운데) -> 라즈베리파이 GND
    엔코더 A                         -> GPIO 27
    엔코더 B                         -> GPIO 22
    엔코더 S1(버튼)                   -> GPIO 17
    엔코더 S2(버튼)                   -> 라즈베리파이 GND

주의:
    display_module.py(LCD 드라이버)가 RPi.GPIO를 사용하므로,
    같은 프로세스에서 gpiozero(lgpio)를 함께 쓰면 "GPIO busy" 충돌이 납니다.
    그래서 이 모듈도 RPi.GPIO로 통일했습니다.

사용 전 설치 필요:
    pip install RPi.GPIO
"""

import RPi.GPIO as GPIO
import time

# ---- 설정값 (실제 배선한 GPIO 번호) ----
ENCODER_PIN_A = 27
ENCODER_PIN_B = 22
BUTTON_PIN = 17

# 로터리 엔코더로 선택할 수 있는 언어 목록
LANGUAGES = ["ko", "en", "ja", "zh"]
LANGUAGE_LABELS = {
    "ko": "한국어",
    "en": "English",
    "ja": "日本語",
    "zh": "中文",
}

_current_language_index = 0

# 버튼 디바운스용 (짧은 시간 내 중복 눌림 방지)
_last_button_time = 0
_BUTTON_DEBOUNCE_SEC = 0.2

_last_state_a = None
_on_clockwise_cb = None
_on_counterclockwise_cb = None
_on_button_pressed_cb = None


def get_current_language() -> str:
    return LANGUAGES[_current_language_index]


def get_current_language_label() -> str:
    return LANGUAGE_LABELS[get_current_language()]


def _handle_clockwise():
    global _current_language_index
    _current_language_index = (_current_language_index + 1) % len(LANGUAGES)
    print(f"[입력 모듈] 언어 선택 -> {get_current_language_label()}")


def _handle_counterclockwise():
    global _current_language_index
    _current_language_index = (_current_language_index - 1) % len(LANGUAGES)
    print(f"[입력 모듈] 언어 선택 -> {get_current_language_label()}")


def _decode_rotation(channel):
    """A핀 상태 변화 인터럽트 콜백. B핀과 비교해서 회전 방향 판별."""
    global _last_state_a

    state_a = GPIO.input(ENCODER_PIN_A)
    state_b = GPIO.input(ENCODER_PIN_B)

    if _last_state_a is None:
        _last_state_a = state_a
        return

    if state_a != _last_state_a:
        if state_a != state_b:
            if _on_clockwise_cb:
                _on_clockwise_cb()
        else:
            if _on_counterclockwise_cb:
                _on_counterclockwise_cb()

    _last_state_a = state_a


def _decode_button(channel):
    """버튼 눌림 인터럽트 콜백. 디바운스 처리 포함."""
    global _last_button_time
    now = time.time()
    if now - _last_button_time < _BUTTON_DEBOUNCE_SEC:
        return
    _last_button_time = now

    if _on_button_pressed_cb:
        _on_button_pressed_cb()


def setup_input_handlers(on_button_pressed):
    """
    엔코더 회전(언어 선택) + 버튼(촬영 트리거) 핸들러를 등록한다.

    Args:
        on_button_pressed: 버튼을 눌렀을 때 실행할 콜백 함수 (main.py에서 전달)

    Returns:
        None (RPi.GPIO는 콜백을 내부에서 계속 유지하므로 별도 참조 유지 불필요)
    """
    global _on_clockwise_cb, _on_counterclockwise_cb, _on_button_pressed_cb, _last_state_a

    _on_clockwise_cb = _handle_clockwise
    _on_counterclockwise_cb = _handle_counterclockwise
    _on_button_pressed_cb = on_button_pressed

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(ENCODER_PIN_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(ENCODER_PIN_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    _last_state_a = GPIO.input(ENCODER_PIN_A)

    GPIO.add_event_detect(ENCODER_PIN_A, GPIO.BOTH, callback=_decode_rotation, bouncetime=5)
    GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=_decode_button, bouncetime=200)

    print(f"[입력 모듈] 준비 완료. 현재 언어: {get_current_language_label()}")


if __name__ == "__main__":
    def _test_button_pressed():
        print(f"[테스트] 버튼 눌림! 현재 언어: {get_current_language_label()}")

    setup_input_handlers(_test_button_pressed)
    print("[테스트] 다이얼을 돌리거나 버튼을 눌러보세요. 종료: Ctrl+C")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup()
