"""
ai_module.py
인포 브릿지 - AI 연동 모듈 (+ 번역 모듈 통합)
[Google AI Studio / Gemini API 버전]

역할:
1. 전처리된 상품 이미지를 Gemini API(비전 기능)로 전송
2. 상품명, 라벨/성분 텍스트, 사용법, 관련 규정(수화물 등)을 인식
3. 사용자가 선택한 언어로 바로 결과를 받음 (번역 모듈 역할 겸용)

사용 전 설치 필요:
    pip install google-genai pillow

API 키 발급:
    https://aistudio.google.com -> Get API key -> Create API key

API 키 설정 (라즈베리파이 터미널에서):
    export GEMINI_API_KEY="여기에_발급받은_키_입력"

    영구 설정하려면 ~/.bashrc 맨 아래에 위 줄을 추가:
    echo 'export GEMINI_API_KEY="키값"' >> ~/.bashrc
    source ~/.bashrc
"""

import json
import os
import socket
import time

from PIL import Image
from google import genai
from google.genai import types

# ---- 설정값 ----
# 참고: gemini-3.6-flash는 속도/비용/무료 등급 balance가 좋은 최신 모델입니다.
# 나중에 더 정확한 인식이 필요하면 "gemini-3.1-pro" 등으로 교체 가능합니다.
MODEL_NAME = os.environ.get("GEMINI_MODEL", "")
API_TIMEOUT_MS = int(os.environ.get("GEMINI_TIMEOUT_MS", "60000"))
API_RETRIES = 1

# 언어 코드 -> 사람이 읽는 이름 매핑 (input_module.py의 LANGUAGE_LABELS와 맞춰야 함)
LANGUAGE_NAMES = {
    "ko": "한국어",
    "en": "English",
    "ja": "日本語",
    "zh": "中文",
}

_client = None  # Gemini 클라이언트 (지연 초기화)


def _get_client() -> genai.Client:
    """Gemini 클라이언트를 준비한다. 처음 호출될 때만 생성."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY 환경변수가 설정되지 않았습니다. "
                "터미널에서 export GEMINI_API_KEY='키값' 을 먼저 실행하세요."
            )
        _client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=API_TIMEOUT_MS),
        )
    return _client


def _get_model_candidates(client: genai.Client) -> list[str]:
    """현재 API 키에서 generateContent가 가능한 모델 목록을 가져온다."""
    if MODEL_NAME:
        return [MODEL_NAME]

    candidates = []
    for model in client.models.list():
        name = getattr(model, "name", "") or ""
        actions = getattr(model, "supported_actions", []) or []
        if name.startswith("models/"):
            name = name[7:]
        if "generateContent" in actions and "flash" in name.lower():
            candidates.append(name)

    preferred = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ]
    return [name for name in preferred if name in candidates] + [
        name for name in candidates if name not in preferred
    ]


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
    전처리된 이미지를 Gemini API로 보내 상품 정보를 인식하고,
    target_language_code 언어로 번역된 결과를 dict로 반환한다.
    """
    try:
        try:
            socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=5).close()
        except OSError as error:
            raise ConnectionError("Google API 서버에 연결할 수 없습니다. Wi-Fi를 확인하세요.") from error

        client = _get_client()
        with Image.open(image_path) as image:
            prompt = _build_prompt(target_language_code)
            response = None
            last_error = None
            model_candidates = _get_model_candidates(client)
            if not model_candidates:
                raise RuntimeError("이 API 키에서 사용할 수 있는 Flash 모델이 없습니다.")
            print(f"[AI 연동 모듈] 사용할 모델: {model_candidates[0]}", flush=True)
            for model_name in model_candidates:
                for attempt in range(API_RETRIES + 1):
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[image, prompt],
                        )
                        break
                    except Exception as error:
                        last_error = error
                        error_text = str(error).lower()
                        model_error = "404" in error_text or "model" in error_text
                        if model_error and model_name != model_candidates[-1]:
                            print(
                                f"[AI 연동 모듈] 모델 변경: {model_name} -> 다음 모델",
                                flush=True,
                            )
                            break
                        if attempt == API_RETRIES:
                            raise
                        print(
                            f"[AI 연동 모듈] API 재시도 {attempt + 1}/{API_RETRIES}: "
                            f"{error}",
                            flush=True,
                        )
                        time.sleep(2 ** attempt)
                if response is not None:
                    break
            if response is None and last_error is not None:
                raise last_error
    except Exception as e:
        error_text = str(e)
        print(f"[AI 연동 모듈] API 호출 실패({type(e).__name__}): {error_text}", flush=True)
        if isinstance(e, ConnectionError):
            message = "Wi-Fi 연결을 확인해 주세요."
        elif "401" in error_text or "403" in error_text:
            message = "Gemini API 키를 확인해 주세요."
        elif "404" in error_text or "model" in error_text.lower():
            message = "사용 가능한 Gemini Flash 모델이 없습니다. API 키 권한을 확인해 주세요."
        elif "429" in error_text:
            message = "Gemini API 사용량 제한입니다. 잠시 후 다시 시도해 주세요."
        else:
            message = "서버 응답 지연 또는 API 오류입니다. 잠시 후 다시 시도해 주세요."
        return {
            "product_name": "",
            "category": "",
            "label_text_summary": message,
            "usage": "",
            "travel_regulations": "",
            "confidence": "낮음",
        }

    raw_text = (response.text or "").strip()

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
