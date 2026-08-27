"""
main.py
인포 브릿지 - 메인 실행 파일 (로터리 엔코더 전용 버전, 터치 기능 제거)

동작 흐름:
1. 대기 화면: 로터리 엔코더로 언어 선택 (화면에 표시)
2. 버튼 누르면: 촬영 -> 전처리 -> "인식 중" 로딩 화면 -> AI 인식/번역 -> 결과 화면
3. 결과 화면에서 다이얼을 돌리면 스크롤, 버튼을 다시 누르면 대기 화면으로 복귀

참고:
    이 LCD 보드(ST7796 컨트롤러)는 실제로는 터치 핀이 배선되어 있지 않아
    터치 기능은 포기하고, 로터리 엔코더(회전+클릭 버튼)만으로 조작합니다.

배선 (input_module.py 기준):
    엔코더 C(공통)   -> GND
    엔코더 A         -> GPIO 27
    엔코더 B         -> GPIO 22
    엔코더 S1(버튼)   -> GPIO 17
    엔코더 S2(버튼)   -> GND

사용 전 설치 필요:
    pip install google-genai pillow numpy
    sudo apt install -y python3-picamera2 python3-pygame

실행:
    export GEMINI_API_KEY="키값"
    python3 main.py
"""

import threading

import pygame

from capture_module import capture_and_preprocess, close_camera, get_preview_frame
from ai_module import recognize_and_translate
from inventory_module import lookup_stock
from input_module import (
    get_current_language,
    get_current_language_label,
    RotaryEncoder,
    ENCODER_PIN_A,
    ENCODER_PIN_B,
    BUTTON_PIN,
    Button,
    _handle_clockwise,
    _handle_counterclockwise,
)
import display_module as display

# ---- 앱 상태 (모듈 전역, 여러 스레드에서 접근하므로 lock으로 보호) ----
_state_lock = threading.Lock()
_app_state = "waiting"      # "waiting" | "preview" | "loading" | "result"
_current_result = None      # AI 인식 결과 dict
_scroll_offset = 0          # 결과 화면 스크롤 위치 (픽셀)
_max_scroll = 0              # 스크롤 가능한 최대 픽셀
_render_requested = threading.Event()

SCROLL_STEP = 40  # 다이얼 한 칸당 스크롤 이동량(픽셀)


def _run_capture_pipeline():
    """
    버튼이 눌렸을 때 별도 스레드에서 실행되는 촬영-인식 파이프라인.
    """
    global _app_state, _current_result, _scroll_offset

    with _state_lock:
        _app_state = "preview"
    _render_requested.set()

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
                "stock_info": None,
            }
            _app_state = "result"
            _scroll_offset = 0
        return

    with _state_lock:
        _app_state = "loading"
    _render_requested.set()

    result = recognize_and_translate(image_path, target_language_code=language_code)
    result["stock_info"] = lookup_stock(result.get("product_name", ""))

    with _state_lock:
        _current_result = result
        _app_state = "result"
        _scroll_offset = 0
    _render_requested.set()


def on_button_pressed():
    """
    엔코더 버튼 콜백 (gpiozero 백그라운드 스레드에서 호출됨).
    - 대기 화면일 때: 촬영 파이프라인 시작
    - 결과 화면일 때: 대기 화면으로 복귀
    - 촬영/로딩 중일 때: 무시 (중복 실행 방지)
    """
    with _state_lock:
        current = _app_state

    if current == "waiting":
        threading.Thread(target=_run_capture_pipeline, daemon=True).start()
    elif current == "result":
        with _state_lock:
            globals()["_app_state"] = "waiting"
        _render_requested.set()


def on_dial_scroll(delta: int):
    """결과 화면에서 스크롤 이동. delta: +1(시계방향) 또는 -1(반시계방향)"""
    global _scroll_offset
    with _state_lock:
        new_offset = _scroll_offset + delta * SCROLL_STEP
        new_offset = max(0, min(new_offset, _max_scroll))
        _scroll_offset = new_offset
    _render_requested.set()
    print(
        f"[스크롤] 방향={'아래' if delta > 0 else '위'}, "
        f"위치={new_offset}/{_max_scroll}",
        flush=True,
    )


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

    encoder = None
    button = None
    try:
        encoder = RotaryEncoder(
            ENCODER_PIN_A,
            ENCODER_PIN_B,
            on_clockwise=clockwise_combined,
            on_counterclockwise=counterclockwise_combined,
        )
        button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.2)
        button.when_pressed = on_button_pressed

        print("[메인] 준비 완료. 다이얼을 돌려 언어를 선택하고, 버튼을 눌러 촬영을 시작하세요.", flush=True)
        print("[메인] 엔코더 입력 방식: 고속 폴링", flush=True)
        print("[메인] 종료하려면 창을 닫거나 ESC를 누르세요.", flush=True)

        clock = pygame.time.Clock()
        running = True
        last_render_key = None
        _render_requested.set()

        while running:
            button.poll()

            # ---- 임시: 엔코더 배선 확인/테스트용 키보드 입력 ----
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_RIGHT:
                        clockwise_combined()
                    elif event.key == pygame.K_LEFT:
                        counterclockwise_combined()
                    elif event.key == pygame.K_SPACE:
                        on_button_pressed()

            with _state_lock:
                current_state = _app_state
                result = _current_result
                offset = _scroll_offset

            if current_state == "preview":
                display.draw_camera_preview(get_preview_frame())
            else:
                language_label = get_current_language_label() if current_state == "waiting" else None
                render_key = (current_state, language_label, id(result), offset)
                if _render_requested.is_set() or render_key != last_render_key:
                    if current_state == "waiting":
                        display.draw_waiting_screen(language_label)
                    elif current_state == "loading":
                        display.draw_loading_screen("인식 중입니다...")
                    elif current_state == "result":
                        total_height = display.draw_result_screen(result, offset)
                        visible_height = display.SCREEN_HEIGHT - 64
                        _max_scroll = max(0, total_height - visible_height)
                    last_render_key = render_key
                    _render_requested.clear()

            clock.tick(display.FPS)
    finally:
        close_camera()
        if button is not None:
            button.close()
        if encoder is not None:
            encoder.close()
        display.quit_display()


if __name__ == "__main__":
    main()
