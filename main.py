"""
main.py
인포 브릿지 - 메인 실행 파일 (화면 출력 모듈 통합 버전)

동작 흐름:
1. 대기 화면: 로터리 엔코더로 언어 선택 (화면에 표시)
2. 버튼 누르면: 촬영 -> 전처리 -> "인식 중" 로딩 화면 -> AI 인식/번역 -> 결과 화면
3. 결과 화면에서 다이얼을 돌리면 스크롤, 버튼을 다시 누르면 대기 화면으로 복귀

주의:
- pygame은 계속 화면을 갱신해줘야 해서, gpiozero의 signal.pause() 대신
  while 루프를 직접 돌리는 구조로 바뀌었습니다.
- 버튼/엔코더 콜백은 gpiozero가 백그라운드 스레드에서 처리하고,
  메인 루프는 "지금 상태가 뭔지"만 보고 화면을 다시 그립니다.

배선 (input_module.py 기준):
    엔코더 C(공통)   -> GND
    엔코더 A         -> GPIO 27
    엔코더 B         -> GPIO 22
    엔코더 S1(버튼)   -> GPIO 17
    엔코더 S2(버튼)   -> GND

사용 전 설치 필요:
    pip install gpiozero anthropic pillow
    sudo apt install -y python3-picamera2 python3-pygame

실행:
    export ANTHROPIC_API_KEY="키값"
    python3 main.py
"""

import threading

import pygame

from capture_module import capture_and_preprocess, close_camera, get_preview_frame
from ai_module import recognize_and_translate
from input_module import (
    get_current_language,
    get_current_language_label,
    RotaryEncoder,
    ENCODER_PIN_A,
    ENCODER_PIN_B,
    BUTTON_PIN,
    _handle_clockwise,
    _handle_counterclockwise,
)
from gpiozero import Button
import display_module as display
import touch_module as touch

# ---- 앱 상태 (모듈 전역, 여러 스레드에서 접근하므로 lock으로 보호) ----
_state_lock = threading.Lock()
_app_state = "waiting"      # "waiting" | "preview" | "loading" | "result"
_current_result = None      # AI 인식 결과 dict
_scroll_offset = 0          # 결과 화면 스크롤 위치 (픽셀)
_max_scroll = 0              # 스크롤 가능한 최대 픽셀 (결과 화면 그릴 때 갱신됨)

SCROLL_STEP = 20  # 다이얼 한 칸당 스크롤 이동량(픽셀)


def _run_capture_pipeline():
    """
    버튼이 눌렸을 때 별도 스레드에서 실행되는 촬영-인식 파이프라인.
    (메인 스레드는 화면 갱신에 집중해야 하므로, 시간이 걸리는 작업은 여기서 처리)
    """
    global _app_state, _current_result, _scroll_offset

    with _state_lock:
        _app_state = "preview"

    language_code = get_current_language()

    try:
        image_path = capture_and_preprocess()
    except Exception as e:
        close_camera()      
        print(f"[메인] 촬영 중 오류 발생: {e}")
        with _state_lock:
            _current_result = {
                "product_name": "",
                "category": "",
                "label_text_summary": "촬영 중 오류가 발생했습니다. 다시 시도해 주세요.",
                "usage": "",
                "travel_regulations": "",
                "confidence": "",
            }
            _app_state = "result"
            _scroll_offset = 0
        return

    with _state_lock:
        _app_state = "loading"

    result = recognize_and_translate(image_path, target_language_code=language_code)

    with _state_lock:
        _current_result = result
        _app_state = "result"
        _scroll_offset = 0


def on_button_pressed():
    """
    엔코더 버튼 콜백 (gpiozero 백그라운드 스레드에서 호출됨).
    - 대기 화면일 때: 촬영 파이프라인 시작
    - 결과 화면일 때: 대기 화면으로 복귀
    - 로딩 중일 때: 무시 (중복 촬영 방지)
    """
    global _app_state

    with _state_lock:
        current = _app_state

    if current == "waiting":
        threading.Thread(target=_run_capture_pipeline, daemon=True).start()
    elif current == "result":
        with _state_lock:
            _app_state = "waiting"
    # loading 중에는 버튼 무시


def on_dial_scroll(delta: int):
    """
    결과 화면에서 스크롤 이동. delta: +1(시계방향) 또는 -1(반시계방향)
    """
    global _scroll_offset

    with _state_lock:
        new_offset = _scroll_offset + delta * SCROLL_STEP
        new_offset = max(0, min(new_offset, _max_scroll))
        _scroll_offset = new_offset


def clockwise_combined():
    """엔코더 시계방향 회전: 대기 중이면 언어 변경, 결과 화면이면 스크롤"""
    with _state_lock:
        current = _app_state
    if current == "waiting":
        _handle_clockwise()
    else:
        on_dial_scroll(+1)


def counterclockwise_combined():
    """엔코더 반시계방향 회전: 대기 중이면 언어 변경, 결과 화면이면 스크롤"""
    with _state_lock:
        current = _app_state
    if current == "waiting":
        _handle_counterclockwise()
    else:
        on_dial_scroll(-1)


def main():
    global _max_scroll

    display.init_display()
    touch.init_touch()

    encoder = RotaryEncoder(
        ENCODER_PIN_A,
        ENCODER_PIN_B,
        on_clockwise=clockwise_combined,
        on_counterclockwise=counterclockwise_combined,
    )
    button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.2)
    button.when_pressed = on_button_pressed

    print("[메인] 준비 완료. 다이얼을 돌려 언어를 선택하고, 버튼을 눌러 촬영을 시작하세요.")
    print("[메인] 종료하려면 창을 닫거나 ESC를 누르세요.")

    clock = pygame.time.Clock()
    running = True

    # 스와이프 제스처 감지용 (터치 다운 시작 좌표 기록)
    swipe_start_pos = None
    touch_start_pos = None
    SWIPE_MIN_DISTANCE = 40  # 이 픽셀 이상 이동해야 스와이프로 인정

    while running:
        touch_pos = touch.read_touch_point(display.SCREEN_WIDTH, display.SCREEN_HEIGHT)
        if touch_pos is not None:
            if touch_start_pos is None:
                touch_start_pos = touch_pos
        elif touch_start_pos is not None:
            touch_pos = touch_start_pos

            with _state_lock:
                current = _app_state

            if current == "waiting" and display.is_point_in_rect(touch_pos, display.CAPTURE_BUTTON_RECT):
                on_button_pressed()
            elif current == "result" and display.is_point_in_rect(touch_pos, display.RETAKE_BUTTON_RECT):
                on_button_pressed()
            elif current == "waiting":
                dx = touch_pos[0] - touch_start_pos[0]
                if dx > SWIPE_MIN_DISTANCE:
                    counterclockwise_combined()
                elif dx < -SWIPE_MIN_DISTANCE:
                    clockwise_combined()

            touch_start_pos = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                # ---- 임시: 다이얼 배선 전 키보드 테스트용 ----
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RIGHT:
                    clockwise_combined()
                elif event.key == pygame.K_LEFT:
                    counterclockwise_combined()
                elif event.key == pygame.K_SPACE:
                    on_button_pressed()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 터치스크린도 pygame에서는 마우스 이벤트로 들어옴
                swipe_start_pos = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                touch_pos = event.pos

                with _state_lock:
                    current = _app_state

                # 1. 버튼 영역 터치 판정 (촬영하기 / 다시 촬영)
                if current == "waiting" and display.is_point_in_rect(touch_pos, display.CAPTURE_BUTTON_RECT):
                    on_button_pressed()
                elif current == "result" and display.is_point_in_rect(touch_pos, display.RETAKE_BUTTON_RECT):
                    on_button_pressed()
                # 2. 버튼이 아니면 스와이프(좌우 드래그) 판정 -> 언어 변경 (대기 화면에서만)
                elif swipe_start_pos is not None and current == "waiting":
                    dx = touch_pos[0] - swipe_start_pos[0]
                    if dx > SWIPE_MIN_DISTANCE:
                        counterclockwise_combined()  # 오른쪽으로 스와이프 -> 이전 언어
                    elif dx < -SWIPE_MIN_DISTANCE:
                        clockwise_combined()          # 왼쪽으로 스와이프 -> 다음 언어

                swipe_start_pos = None

        with _state_lock:
            current_state = _app_state
            result = _current_result
            offset = _scroll_offset

        if current_state == "waiting":
            display.draw_waiting_screen(get_current_language_label())
        elif current_state == "preview":
            display.draw_camera_preview(get_preview_frame())
        elif current_state == "loading":
            display.draw_loading_screen("인식 중입니다...")
        elif current_state == "result":
            total_height = display.draw_result_screen(result, offset)
            _max_scroll = max(0, total_height - display.SCREEN_HEIGHT + 40)

        clock.tick(display.FPS)

    close_camera()
    touch.close_touch()
    display.quit_display()


if __name__ == "__main__":
    main()
