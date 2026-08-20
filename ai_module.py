"""
ai_module.py
인포 브릿지 - AI 연동 모듈 (+ 번역 모듈 통합)

역할:
1. 전처리된 상품 이미지를 Claude API(비전 기능)로 전송
2. 상품명, 라벨/성분 텍스트, 사용법, 관련 규정(수화물 등)을 인식
3. 사용자가 선택한 언어로 바로 결과를 받음 (번역 모듈 역할 겸용)

사용 전 설치 필요:
    pip install anthropic

API 키 설정 (라즈베리파이 터미널에서, 매번 새 터미널 열 때마다 필요):
    export ANTHROPIC_API_KEY="여기에_발급받은_키_입력"

    또는 영구 설정하려면 ~/.bashrc 맨 아래에 위 줄을 추가하고:
    source ~/.bashrc
"""

import base64
import json
import os
from anthropic import Anthropic

# ---- 설정값 ----
MODEL_NAME = "claude-sonnet-5"   # 속도/비용 균형이 좋은 모델. 정확도를 더 높이려면 "claude-opus-5"로 교체 가능

# 언어 코드 -> 사람이 읽는 이름 매핑 (로터리 엔코더로 선택할 언어 목록과 맞추면 됨)
LANGUAGE_NAMES = {
    "ko": "한국어",
    "en": "English",
    "ja": "日本語",
    "zh": "中文",
}


def _load_image_as_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _build_prompt(target_language_code: str) -> str:
    language_name = LANGUAGE_NAMES.get(target_language_code, target_language_code)

    return f"""당신은 해외여행자를 위한 상품 정보 안내 AI입니다.
첨부된 이미지는 여행자가 궁금해하는 상품(또는 그 라벨/포장지)을 촬영한 사진입니다.

다음 항목을 분석해서, 반드시 아래 JSON 형식으로만 답변하세요.
설명 문장이나 코드블록 표시(```) 없이 순수 JSON만 출력하세요.
모든 텍스트 내용은 "{language_name}"로 작성하세요.

{{
  "product_name": "상품명 (인식 실패 시 빈 문자열)",
  "category": "상품 카테고리 (예: 식품, 화장품, 의약품, 전자제품 등)",
  "label_text_summary": "라벨/포장지에서 읽은 주요 텍스트(성분, 용량 등)를 요약",
  "usage": "사용법 또는 섭취/사용 시 주의사항",
  "travel_regulations": "수화물 반입 관련 규정이나 여행 시 주의할 점 (액체류 용량 제한, 반입 금지 성분 등). 특별히 해당 없으면 '특별한 제한 사항 없음'",
  "confidence": "인식 결과에 대한 확신도 (높음/중간/낮음)"
}}

만약 이미지에서 상품을 인식할 수 없다면, product_name을 빈 문자열로 두고
label_text_summary에 "이미지를 다시 촬영해 주세요"라고 안내하세요."""


def recognize_and_translate(image_path: str, target_language_code: str = "ko") -> dict:
    """
    전처리된 이미지를 Claude API로 보내 상품 정보를 인식하고,
    target_language_code 언어로 번역된 결과를 dict로 반환한다.

    반환 예시:
    {
        "product_name": "...",
        "category": "...",
        "label_text_summary": "...",
        "usage": "...",
        "travel_regulations": "...",
        "confidence": "..."
    }
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다. "
            "터미널에서 export ANTHROPIC_API_KEY='키값' 을 먼저 실행하세요."
        )

    client = Anthropic(api_key=api_key)
    image_b64 = _load_image_as_base64(image_path)
    prompt = _build_prompt(target_language_code)

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
    except Exception as e:
        print(f"[AI 연동 모듈] API 호출 실패: {e}")
        return {
            "product_name": "",
            "category": "",
            "label_text_summary": "네트워크 오류 또는 서버 응답 지연. 다시 시도해 주세요.",
            "usage": "",
            "travel_regulations": "",
            "confidence": "낮음",
        }

    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()

    # 혹시 모델이 코드블록으로 감싸서 응답한 경우 제거
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        print("[AI 연동 모듈] JSON 파싱 실패, 원본 텍스트 반환")
        result = {
            "product_name": "",
            "category": "",
            "label_text_summary": raw_text,
            "usage": "",
            "travel_regulations": "",
            "confidence": "낮음",
        }

    print(f"[AI 연동 모듈] 인식 완료: {result.get('product_name', '(인식 실패)')}")
    return result


if __name__ == "__main__":
    # 단독 테스트: capture_module.py로 찍어둔 이미지가 있다는 가정
    test_image = "captured_processed.jpg"
    if not os.path.exists(test_image):
        print(f"테스트용 이미지가 없습니다: {test_image}")
        print("먼저 python3 capture_module.py 를 실행해서 이미지를 만들어주세요.")
    else:
        result = recognize_and_translate(test_image, target_language_code="ko")
        print(json.dumps(result, ensure_ascii=False, indent=2))
