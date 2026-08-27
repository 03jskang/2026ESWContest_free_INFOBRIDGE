"""
display_module.py
인포 브릿지 - 화면 출력 모듈

역할:
1. 대기 화면: 현재 선택된 언어와 안내 문구 표시
2. 결과 화면: AI 인식 결과(상품명/성분/사용법/여행규정)를 표시, 길면 스크롤
3. 로딩 화면: AI 서버 응답 대기 중임을 표시

화면 크기는 3.5인치 LCD 규격(480x320)에 맞춰뒀지만,
지금은 HDMI 모니터에서도 그냥 작은 창으로 잘 뜹니다.
나중에 LCD로 교체할 때는 SCREEN_WIDTH/HEIGHT 값만 유지하면 됩니다.

사용 전 설치 필요:
    sudo apt install -y python3-pygame
"""

import os

# LCD로 출력하므로 실제 모니터(HDMI) 없이도 pygame이 동작하도록
# "화면 없는(headless)" SDL 드라이버를 사용한다.
# 만약 디버깅용으로 HDMI 모니터에도 같이 띄우고 싶다면 아래 줄을 주석 처리하면 된다.
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from PIL import Image
import ili9486_driver

# ---- 화면 설정 ----
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 320
FPS = 30

# ---- 색상 (RGB) ----
COLOR_BG = (20, 20, 30)
COLOR_TEXT = (240, 240, 240)
COLOR_LABEL = (120, 180, 255)
COLOR_ACCENT = (255, 200, 80)
COLOR_MUTED = (150, 150, 150)

# ---- 폰트 크기 ----
FONT_SIZE_TITLE = 22
FONT_SIZE_LABEL = 16
FONT_SIZE_BODY = 16
FONT_SIZE_HINT = 13

# 화면 표시 상태 (모듈 전역)
_screen = None
_font_title = None
_font_label = None
_font_body = None
_font_hint = None
_font_sets = {}

# 결과 화면 스크롤 위치 (버튼/엔코더로 조절)
_scroll_offset = 0

# ---- 터치 버튼 영역 (x, y, width, height) ----
# main.py에서 이 좌표를 그대로 가져다 터치/클릭 판정에 씀
CAPTURE_BUTTON_RECT = (SCREEN_WIDTH // 2 - 70, SCREEN_HEIGHT - 60, 140, 44)
RETAKE_BUTTON_RECT = (SCREEN_WIDTH // 2 - 70, SCREEN_HEIGHT - 60, 140, 44)

COLOR_BUTTON = (60, 100, 200)
COLOR_BUTTON_TEXT = (255, 255, 255)


def _draw_button(rect: tuple, label: str):
    """버튼 사각형과 라벨을 그린다. rect = (x, y, w, h)"""
    x, y, w, h = rect
    pygame.draw.rect(_screen, COLOR_BUTTON, (x, y, w, h), border_radius=10)
    label_surf = _render_text(label, _font_label, COLOR_BUTTON_TEXT)
    label_rect = label_surf.get_rect(center=(x + w // 2, y + h // 2))
    _screen.blit(label_surf, label_rect)


def _flip_to_lcd():
    """
    pygame이 그린 화면(_screen)을 그대로 캡처해서
    실제 3.5인치 SPI LCD에 전송한다.
    기존 pygame.display.flip() 자리를 대신 호출하면 된다.
    """
    pygame.display.flip()  # pygame 내부적으로도 최신 상태 유지 (디버깅/이벤트 처리용)

    raw = pygame.image.tostring(_screen, "RGB")
    img = Image.frombytes("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), raw)
    ili9486_driver.display_image(img)


def is_point_in_rect(point: tuple, rect: tuple) -> bool:
    """터치/클릭 좌표가 버튼 영역 안에 있는지 판정"""
    px, py = point
    x, y, w, h = rect
    return x <= px <= x + w and y <= py <= y + h


def init_display():
    """pygame을 초기화하고 화면을 준비한다. 프로그램 시작 시 한 번만 호출."""
    global _screen, _font_title, _font_label, _font_body, _font_hint, _font_sets

    pygame.init()
    _screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("인포 브릿지")

    # 실제 3.5인치 LCD (SPI, ILI9486) 초기화
    ili9486_driver.init()

    # 한국어/중국어/일본어 글리프가 함께 있는 CJK 폰트를 먼저 사용한다.
    font_candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJKkr-Regular.otf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ]
    cjk_candidates = set(font_candidates[:-1])
    _font_sets = {}
    loaded_cjk_font = False
    for size in [FONT_SIZE_TITLE, FONT_SIZE_LABEL, FONT_SIZE_BODY, FONT_SIZE_HINT]:
        fonts = []
        for candidate in font_candidates:
            try:
                fonts.append(pygame.font.Font(candidate, size))
                if candidate in cjk_candidates:
                    loaded_cjk_font = True
            except (FileNotFoundError, OSError):
                continue
        if not fonts:
            fonts.append(pygame.font.Font(None, size))
        _font_sets[size] = fonts

    _font_title = _font_sets[FONT_SIZE_TITLE][0]
    _font_label = _font_sets[FONT_SIZE_LABEL][0]
    _font_body = _font_sets[FONT_SIZE_BODY][0]
    _font_hint = _font_sets[FONT_SIZE_HINT][0]

    if not loaded_cjk_font:
        print(
            "[화면 출력 모듈] 경고: CJK 폰트를 찾지 못했습니다. "
            "'sudo apt install fonts-noto-cjk'를 설치하세요.",
            flush=True,
        )


def _font_supports(font, char: str) -> bool:
    """폰트에 문자의 글리프가 있는지 확인한다."""
    if char.isspace() or char in ".,!?/:-()[]{}<>·|+=" or char.isascii():
        return True
    metrics = font.metrics(char)
    return bool(metrics and metrics[0] is not None)


def _font_for_char(font, char: str):
    """기본 폰트가 지원하지 않는 문자를 지원 폰트로 대체한다."""
    for font_group in _font_sets.values():
        for candidate in font_group:
            if candidate.get_height() == font.get_height() and _font_supports(candidate, char):
                return candidate
    return font


def _render_text(text: str, font, color):
    """문자별 폴백 폰트를 적용해 한 줄을 렌더링한다."""
    if not text:
        return font.render(text, True, color)

    groups = []
    current_font = _font_for_char(font, text[0])
    current_text = text[0]
    for char in text[1:]:
        char_font = _font_for_char(font, char)
        if char_font == current_font:
            current_text += char
        else:
            groups.append((current_font, current_text))
            current_font = char_font
            current_text = char
    groups.append((current_font, current_text))

    width = sum(group_font.size(group_text)[0] for group_font, group_text in groups)
    surface = pygame.Surface((max(1, width), font.get_height()), pygame.SRCALPHA)
    x = 0
    for group_font, group_text in groups:
        rendered = group_font.render(group_text, True, color)
        surface.blit(rendered, (x, 0))
        x += rendered.get_width()
    return surface


def _text_width(text: str, font) -> int:
    return _render_text(text, font, COLOR_TEXT).get_width()


def _wrap_text(text: str, font, max_width: int) -> list:
    """긴 텍스트를 화면 너비에 맞게 여러 줄로 나눈다."""
    if not text:
        return [""]

    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        if _text_width(test_line, font) > max_width:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines


def draw_waiting_screen(language_label: str):
    """대기 화면: 언어 선택 안내 표시"""
    _screen.fill(COLOR_BG)

    title_surf = _render_text("인포 브릿지", _font_title, COLOR_TEXT)
    _screen.blit(title_surf, (20, 30))

    label_surf = _render_text("촬영할 준비가 되었습니다", _font_label, COLOR_MUTED)
    _screen.blit(label_surf, (20, 80))

    lang_surf = _render_text(f"언어: {language_label}", _font_title, COLOR_ACCENT)
    _screen.blit(lang_surf, (20, 130))

    hint1 = _render_text("다이얼을 돌리거나 화면을 좌우로 스와이프해", _font_hint, COLOR_MUTED)
    _screen.blit(hint1, (20, 180))
    hint2 = _render_text("언어를 선택하세요", _font_hint, COLOR_MUTED)
    _screen.blit(hint2, (20, 200))

    _draw_button(CAPTURE_BUTTON_RECT, "촬영하기")

    _flip_to_lcd()


def draw_loading_screen(message: str = "인식 중입니다..."):
    """AI 서버 응답 대기 중 화면"""
    _screen.fill(COLOR_BG)

    msg_surf = _render_text(message, _font_title, COLOR_ACCENT)
    _screen.blit(msg_surf, (20, 140))

    hint_surf = _render_text("잠시만 기다려 주세요", _font_hint, COLOR_MUTED)
    _screen.blit(hint_surf, (20, 180))

    _flip_to_lcd()


def draw_camera_preview(frame, message: str = "촬영 중입니다..."):
    """Picamera2 프리뷰 프레임과 촬영 상태를 표시한다."""
    _screen.fill(COLOR_BG)

    if frame is not None:
        preview = pygame.image.fromstring(
            frame.tobytes(), frame.size, "RGB"
        )
        preview = pygame.transform.scale(preview, (SCREEN_WIDTH, SCREEN_HEIGHT))
        _screen.blit(preview, (0, 0))

    overlay = pygame.Surface((SCREEN_WIDTH, 42), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    _screen.blit(overlay, (0, 0))
    message_surf = _render_text(message, _font_label, COLOR_TEXT)
    _screen.blit(message_surf, (20, 12))

    _flip_to_lcd()


def draw_result_screen(result: dict, scroll_offset: int = 0):
    """
    AI 인식 결과 화면. 내용이 길면 scroll_offset(픽셀)만큼 위로 밀어서 표시.
    """
    _screen.fill(COLOR_BG)

    content_width = SCREEN_WIDTH - 40  # 좌우 여백 20px씩
    content_bottom = SCREEN_HEIGHT - 64
    y = 20 - scroll_offset
    line_height = 20

    def draw_section(label: str, value: str, y_pos: int) -> int:
        """라벨+내용을 그리고, 다음 섹션이 시작될 y좌표를 반환"""
        if not value:
            return y_pos
        if y_pos > -line_height and y_pos < content_bottom:
            label_surf = _render_text(label, _font_label, COLOR_LABEL)
            _screen.blit(label_surf, (20, y_pos))
        y_pos += line_height

        lines = _wrap_text(value, _font_body, content_width)
        for line in lines:
            if y_pos > -line_height and y_pos < content_bottom:
                line_surf = _render_text(line, _font_body, COLOR_TEXT)
                _screen.blit(line_surf, (20, y_pos))
            y_pos += line_height
        return y_pos + 10  # 섹션 간 여백

    product_name = result.get("product_name") or "(인식 실패)"
    y = draw_section("상품명", product_name, y)
    y = draw_section("카테고리", result.get("category", ""), y)
    y = draw_section("라벨/성분 요약", result.get("label_text_summary", ""), y)
    y = draw_section("사용법", result.get("usage", ""), y)
    y = draw_section("여행 시 유의사항", result.get("travel_regulations", ""), y)

    stock_info = result.get("stock_info")
    if stock_info:
        stock_text = (
            f"매장: {stock_info.get('store', '')} / "
            f"재고: {stock_info.get('stock', '')} / "
            f"위치: {stock_info.get('location', '')} / "
            f"가격: {stock_info.get('price', '')}원"
        )
        y = draw_section("매장 정보", stock_text, y)
        y = draw_section("상품 설명", stock_info.get("description", ""), y)

    # 하단 고정 영역: 스크롤과 무관하게 항상 같은 자리에 재촬영 버튼 표시
    pygame.draw.rect(_screen, COLOR_BG, (0, SCREEN_HEIGHT - 64, SCREEN_WIDTH, 64))
    _draw_button(RETAKE_BUTTON_RECT, "다시 촬영")

    _flip_to_lcd()

    # 스크롤 가능한 전체 콘텐츠 높이를 반환 (스크롤 한계 계산용)
    return y + scroll_offset


def process_events() -> bool:
    """
    pygame 이벤트 큐를 처리한다 (창 닫기 등).
    Returns:
        False면 프로그램 종료 요청, True면 계속 진행
    """
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return False
    return True


def quit_display():
    pygame.quit()
