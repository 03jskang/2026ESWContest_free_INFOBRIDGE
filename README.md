# Info-Bridge (인포 브릿지)

해외 여행객을 위한 온디바이스 비전 AI 기반 독립형 상품 안내 시스템입니다.
카메라로 상품을 촬영하면 상품명·카테고리·라벨 성분 요약·사용법·항공 반입 규정을
사용자가 선택한 언어로 안내하고, 매장 재고(CSV)와 매칭해 위치·가격 정보도 함께 보여줍니다.

라즈베리파이 4B + Google Gemini API를 결합해, 별도 앱 설치 없이 전원만 켜면
바로 쓸 수 있는 휴대형 Standalone 디바이스로 설계했습니다.

## 팀 정보

- 팀명: 인포브릿지
- 팀장: 강주성 — 개발 총괄, SW 구축
- 팀원: 서하진 — 3D 모델링, 아날로그 설비
- 팀원: 김동민 — 3D 모델링 보조, 문서 작성 보조
- 팀원: 조범근 — SW 구축 및 OS 초기 구성
- 팀원: 이민주 — SW 개발 보조, 문서 작성

## 하드웨어 구성

- Raspberry Pi 4B (4GB)
- 5MP MIPI 카메라
- 3.5인치 SPI LCD, 480×320, ILI9486 컨트롤러
- 로터리 엔코더(푸시 버튼 내장)

## 소프트웨어 환경

- Raspberry Pi OS (Bookworm, 64-bit) / Python 3
- 주요 라이브러리: `picamera2`, `pygame`, `RPi.GPIO`, `google-genai`, `spidev`

## 설치

```bash
git clone https://github.com/03jskang/2026ESWContest_free_INFOBRIDGE.git
cd 2026ESWContest_free_INFOBRIDGE
pip install picamera2 pygame RPi.GPIO google-genai spidev
```

## Gemini API 키 설정

`ai_module.py`는 `GEMINI_API_KEY` 환경변수가 없으면 즉시 오류를 내며 종료합니다.
아래 방법 중 하나로 먼저 설정하세요.

**일회성 (터미널 세션에서만 유효)**

```bash
export GEMINI_API_KEY="여기에_발급받은_키_입력"
```

**영구 설정**

```bash
echo 'export GEMINI_API_KEY="키값"' >> ~/.bashrc
source ~/.bashrc
```

**자동 실행(systemd)으로 등록한 경우** — 아래 파일에 키를 넣으면 서비스가 자동으로 읽습니다.

```
~/.config/info-bridge.env
```

## 실행

```bash
python main.py
```

엔코더 하드웨어가 아직 준비되지 않았다면, 키보드로도 동일하게 조작할 수 있습니다.

| 키 | 동작 |
|---|---|
| ← / → | 엔코더 반시계 / 시계 방향 회전과 동일 (언어 선택 또는 결과 화면 스크롤) |
| Space | 버튼 클릭과 동일 (촬영 시작 또는 대기 화면 복귀) |

## 부팅 시 자동 실행 설정

```bash
sudo bash install_autostart.sh
```

systemd 서비스(`info-bridge.service`)로 등록되어 전원이 켜지면 `main.py`가 자동 실행됩니다.

```bash
# 서비스 상태 확인
sudo systemctl status info-bridge.service

# 실시간 로그 확인
sudo journalctl -u info-bridge.service -f
```

## 동작 흐름 (상태 머신)

```
전원 ON / 초기화
   ↓
대기 화면 (엔코더로 언어 선택)
   ↓ 버튼 클릭
촬영 및 프리뷰 (2초 프리뷰 후 정지 이미지 촬영)
   ↓
AI 인식 및 번역 (Gemini API 호출 + 매장 재고 매칭)
   ↓
결과 표시 (엔코더로 스크롤)
   ↓ 버튼 클릭
대기 화면으로 복귀
```

## 파일 구성

| 파일 | 역할 |
|---|---|
| `main.py` | 전체 상태(`waiting`/`preview`/`loading`/`result`) 관리 및 각 모듈 호출 |
| `input_module.py` | 로터리 엔코더 회전/버튼 클릭 감지 (폴링 방식) |
| `capture_module.py` | 카메라 프리뷰 표시, 정지 이미지 촬영 및 전처리 |
| `ai_module.py` | Gemini API 호출을 통한 상품 인식·번역 |
| `inventory_module.py` | 인식된 상품명과 CSV 매장 데이터 매칭 |
| `display_module.py` | pygame 기반 화면 렌더링 |
| `ili9486_driver.py` | SPI/GPIO 제어를 통한 LCD 저수준 출력 |
| `install_autostart.sh` | 부팅 시 자동 실행용 systemd 서비스 등록 스크립트 |
| `test_camera.py` | 카메라 단독 동작 테스트용 스크립트 |
| `convenience_store_inventory.csv` | 매장 재고 데이터 (기본값) |
| `retail_product_inventory_large.csv` | 매장 재고 데이터 (대용량 샘플) |

## 환경변수로 조정 가능한 값

| 변수 | 기본값 | 설명 |
|---|---|---|
| `GEMINI_API_KEY` | (필수) | Gemini API 키 |
| `GEMINI_MODEL` | - | 사용할 Gemini 모델명 |
| `GEMINI_TIMEOUT_MS` | 60000 | API 응답 타임아웃(ms) |
| `LCD_SPI_SPEED` | 8000000 | LCD SPI 통신 속도(Hz). 화면이 불안정하면 낮춰서 조정 |
| `LCD_COLOR_ORDER` | RGB | 색상이 반전되어 보이면 `BGR`로 변경 |
| `INVENTORY_CSV` | `convenience_store_inventory.csv` | 매장 재고 CSV 파일 경로 교체 |

## 예외 처리

- Wi-Fi/네트워크 오류: 요청 전 서버 연결을 사전 확인하고, 실패 시 지수 백오프로 재시도
- Gemini API 오류: 401/403/404/429 등 에러 코드별 안내 메시지 분기, 모델 후보 순회(fallback)
- JSON 파싱 실패: 원본 응답 텍스트를 화면에 그대로 표시하여 프로그램이 중단되지 않도록 처리
- 카메라 예외: 발생 시 카메라 자원을 정리하고 오류 안내 화면 표시

## 시연 영상

<!-- 유튜브 링크를 여기에 추가하세요 -->
