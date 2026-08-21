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

import pygame

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
    label_surf = _font_label.render(label, True, COLOR_BUTTON_TEXT)
    label_rect = label_surf.get_rect(center=(x + w // 2, y + h // 2))
    _screen.blit(label_surf, label_rect)


def is_point_in_rect(point: tuple, rect: tuple) -> bool:
    """터치/클릭 좌표가 버튼 영역 안에 있는지 판정"""
    px, py = point
    x, y, w, h = rect
    return x <= px <= x + w and y <= py <= y + h


def init_display():
    """pygame을 초기화하고 화면을 준비한다. 프로그램 시작 시 한 번만 호출."""
    global _screen, _font_title, _font_label, _font_body, _font_hint

    pygame.init()
    _screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("인포 브릿지")

    # 한글 폰트: 라즈베리파이 OS 기본 탑재 나눔고딕 계열 시도, 없으면 시스템 기본 폰트로 대체
    font_path = None
    for candidate in [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]:
        try:
            pygame.font.Font(candidate, 10)
            font_path = candidate
            break
        except (FileNotFoundError, OSError):
            continue

    _font_title = pygame.font.Font(font_path, FONT_SIZE_TITLE)
    _font_label = pygame.font.Font(font_path, FONT_SIZE_LABEL)
    _font_body = pygame.font.Font(font_path, FONT_SIZE_BODY)
    _font_hint = pygame.font.Font(font_path, FONT_SIZE_HINT)

    if font_path is None:
        print("[화면 출력 모듈] 경고: 한글 폰트를 찾지 못해 기본 폰트로 대체합니다. "
              "한글이 깨져 보이면 'sudo apt install fonts-nanum'을 설치하세요.")


def _wrap_text(text: str, font, max_width: int) -> list:
    """긴 텍스트를 화면 너비에 맞게 여러 줄로 나눈다."""
    if not text:
        return [""]

    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        if font.size(test_line)[0] > max_width:
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

    title_surf = _font_title.render("인포 브릿지", True, COLOR_TEXT)
    _screen.blit(title_surf, (20, 30))

    label_surf = _font_label.render("촬영할 준비가 되었습니다", True, COLOR_MUTED)
    _screen.blit(label_surf, (20, 80))

    lang_surf = _font_title.render(f"언어: {language_label}", True, COLOR_ACCENT)
    _screen.blit(lang_surf, (20, 130))

    hint1 = _font_hint.render("다이얼을 돌리거나 화면을 좌우로 스와이프해", True, COLOR_MUTED)
    _screen.blit(hint1, (20, 180))
    hint2 = _font_hint.render("언어를 선택하세요", True, COLOR_MUTED)
    _screen.blit(hint2, (20, 200))

    _draw_button(CAPTURE_BUTTON_RECT, "촬영하기")

    pygame.display.flip()


def draw_loading_screen(message: str = "인식 중입니다..."):
    """AI 서버 응답 대기 중 화면"""
    _screen.fill(COLOR_BG)

    msg_surf = _font_title.render(message, True, COLOR_ACCENT)
    _screen.blit(msg_surf, (20, 140))

    hint_surf = _font_hint.render("잠시만 기다려 주세요", True, COLOR_MUTED)
    _screen.blit(hint_surf, (20, 180))

    pygame.display.flip()


def draw_result_screen(result: dict, scroll_offset: int = 0):
    """
    AI 인식 결과 화면. 내용이 길면 scroll_offset(픽셀)만큼 위로 밀어서 표시.
    """
    _screen.fill(COLOR_BG)

    content_width = SCREEN_WIDTH - 40  # 좌우 여백 20px씩
    y = 20 - scroll_offset
    line_height = 20

    def draw_section(label: str, value: str, y_pos: int) -> int:
        """라벨+내용을 그리고, 다음 섹션이 시작될 y좌표를 반환"""
        if not value:
            return y_pos
        if y_pos > -line_height and y_pos < SCREEN_HEIGHT:
            label_surf = _font_label.render(label, True, COLOR_LABEL)
            _screen.blit(label_surf, (20, y_pos))
        y_pos += line_height

        lines = _wrap_text(value, _font_body, content_width)
        for line in lines:
            if y_pos > -line_height and y_pos < SCREEN_HEIGHT:
                line_surf = _font_body.render(line, True, COLOR_TEXT)
                _screen.blit(line_surf, (20, y_pos))
            y_pos += line_height
        return y_pos + 10  # 섹션 간 여백

    product_name = result.get("product_name") or "(인식 실패)"
    y = draw_section("상품명", product_name, y)
    y = draw_section("카테고리", result.get("category", ""), y)
    y = draw_section("라벨/성분 요약", result.get("label_text_summary", ""), y)
    y = draw_section("사용법", result.get("usage", ""), y)
    y = draw_section("여행 시 유의사항", result.get("travel_regulations", ""), y)

    # 하단 고정 영역: 스크롤과 무관하게 항상 같은 자리에 재촬영 버튼 표시
    pygame.draw.rect(_screen, COLOR_BG, (0, SCREEN_HEIGHT - 64, SCREEN_WIDTH, 64))
    _draw_button(RETAKE_BUTTON_RECT, "다시 촬영")

    pygame.display.flip()

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
