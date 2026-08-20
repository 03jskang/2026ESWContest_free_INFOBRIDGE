"""
main.py
인포 브릿지 - 메인 실행 파일 (로터리 엔코더 입력 연동)

동작 흐름:
1. 대기 상태: 로터리 엔코더를 돌려 언어 선택 (input_module.py가 처리)
2. 엔코더 버튼을 누르면: 촬영 -> 전처리 -> AI 인식/번역(선택된 언어로) -> 결과 출력
3. 결과 출력 후 다시 대기 상태로 복귀 (반복)

주의:
- 이 버전은 아직 LCD 대신 터미널에 결과를 출력합니다.
  (2-2 시스템 구성의 "화면 출력 모듈"은 LCD 붙인 뒤 별도로 연결할 예정)

배선 (input_module.py 기준):
    엔코더 C(공통)   -> GND
    엔코더 A         -> GPIO 27
    엔코더 B         -> GPIO 22
    엔코더 S1(버튼)   -> GPIO 17
    엔코더 S2(버튼)   -> GND

사용 전 설치 필요:
    pip install gpiozero anthropic pillow
    sudo apt install -y python3-picamera2

실행:
    export ANTHROPIC_API_KEY="키값"
    python3 main.py
"""

from signal import pause

from capture_module import capture_and_preprocess
from ai_module import recognize_and_translate
from input_module import setup_input_handlers, get_current_language, get_current_language_label


def print_result(result: dict):
    """결과를 보기 좋게 출력. LCD 연결 후에는 이 함수를 화면 출력 함수로 교체."""
    print("\n===== 인식 결과 =====")
    print(f"상품명       : {result.get('product_name') or '(인식 실패)'}")
    print(f"카테고리     : {result.get('category', '')}")
    print(f"라벨/성분 요약: {result.get('label_text_summary', '')}")
    print(f"사용법       : {result.get('usage', '')}")
    print(f"여행 시 유의 : {result.get('travel_regulations', '')}")
    print(f"확신도       : {result.get('confidence', '')}")
    print("======================\n")


def on_button_pressed():
    """엔코더 버튼이 눌렸을 때 실행되는 촬영-인식 파이프라인"""
    language_code = get_current_language()
    language_label = get_current_language_label()

    print(f"[메인] 버튼 입력 감지. 선택된 언어: {language_label}. 촬영을 시작합니다...")
    try:
        image_path = capture_and_preprocess()
    except Exception as e:
        print(f"[메인] 촬영 중 오류 발생: {e}")
        return

    print("[메인] AI 서버로 전송 중... (인터넷 연결 필요)")
    result = recognize_and_translate(image_path, target_language_code=language_code)
    print_result(result)
    print(f"[메인] 대기 상태로 복귀. 다이얼로 언어를 바꾸거나(현재: {get_current_language_label()}), 버튼을 눌러 촬영하세요.")


def main():
    # 엔코더(언어 선택) + 버튼(촬영 트리거) 핸들러 등록
    # encoder, button 변수는 프로그램이 끝날 때까지 참조를 유지해야 콜백이 살아있음
    encoder, button = setup_input_handlers(on_button_pressed=on_button_pressed)

    print("[메인] 준비 완료. 다이얼을 돌려 언어를 선택하고, 버튼을 눌러 촬영을 시작하세요.")
    print("[메인] 종료하려면 Ctrl+C 를 누르세요.")
    pause()  # 인터럽트 방식으로 입력을 계속 대기


if __name__ == "__main__":
    main()
