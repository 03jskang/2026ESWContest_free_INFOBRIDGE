# Infobridge-team-
 한경국립대학교 공과 학부연합 개발 준동아리 2번 공모전 작업 공간입니다.  

[7월: 기획 및 시스템 설계 회의]

7월 1주차: 프로젝트 킥오프 및 기획 회의
해외 여행객을 위한 AI 기반 정보 안내 디바이스 '인포 브릿지' 개발 목표 및 필요성 확립

7월 2주차: 개발 환경 선정 및 시스템 구성 논의
Raspberry Pi 4B 및 Python 3 기반의 임베디드 소프트웨어 개발 환경 확정
입력 처리, 촬영, AI 연동, 번역, 화면 출력 등 5가지 주요 시스템 구성 모듈 구조 논의

7월 3주차: 동작 흐름 설계 및 라이브러리 검토
상태 머신(state machine) 구조를 활용한 전체 동작 흐름 설계
카메라 제어용 picamera 2, LCD 출력용 pygame, 엔코더 입력용 gpio zero 라이브러리 적용 검토

7월 4주차: 담당 업무 세분화 및 개발 계획 확정
팀장 강주성(개발 총괄, 펌웨어 구축), 팀원 조범근(펌웨어 구축), 김동민(SW 개발 보조)의 소프트웨어 업무 구체화
팀원 서하진(3D 모델링, 아날로그 설비), 이민주(SW개발 보조, 아날로그 설비)의 하드웨어 및 외관 설계 업무 구체화

[8월: 모듈 구현 및 하드웨어/소프트웨어 통합 개발]

8월 1주차: 하드웨어 초기화 및 모델링 작업
하드웨어(LCD, 카메라, GPIO) 초기화 및 전원 대기 상태 로직 구현
독립형 임베디드 디바이스 제작을 위한 3D 모델링 및 아날로그 설비 진행

8월 2주차: 입출력 및 촬영 모듈 개발
로터리 엔코더와 버튼 클릭을 인터럽트 방식으로 감지하는 입력 처리 모듈 구현
5MP 카메라 모듈을 통한 촬영 및 이미지 리사이즈/크롭 전처리 로직 구현
3.5인치 LCD(480x320)에 정보를 스크롤하고 표시하는 화면 출력 모듈 구현
->api 넘기는 것은 구현 완료했지만 촬영 preview 구현해야 함. 

카메라 프리뷰는 LCD에 실시간으로 표시하고, 프리뷰 종료 시 마지막 정지 이미지를
Gemini에 전송합니다. 영상 자체를 Gemini에 보내는 것이 아니라 상품 분석에 필요한
한 장의 사진을 보내는 구조입니다.

8월 3주차: 외부 AI 서버 통신 및 번역 모듈 통합
requests 모듈을 이용해 외부 AI 서버(Vision/OCR API)로 이미지를 전송하고 텍스트 및 부가 정보를 조회하는 AI 연동 모듈 개발
AI 서버 결과를 바탕으로 성분 및 규정 등의 정보를 번역하는 모듈 통합
08/23~ 개선 및 기능 추가

8월 4주차: 예외 처리, 디버깅 및 최종 테스트
Wi-Fi 연결 끊김 및 AI 서버 응답 지연에 대비한 타임아웃, 재시도 로직 등 예외 처리 구현
촬영, 번역, 재 촬영으로 이어지는 순환 구조 테스트 및 트러블 슈팅을 통한 최종 마감

<<<<<<< HEAD
## 터치 LCD 배선

XPT2046 터치 컨트롤러 기준:

- `T_IRQ` -> BCM GPIO 26
- `T_CS` -> BCM GPIO 7
- `T_CLK` -> GPIO 11, `T_DIN` -> GPIO 10, `T_DO` -> GPIO 9

터치 좌표가 화면과 반대로 움직이면 `touch_module.py`의 `SWAP_XY`, `INVERT_X`,
`INVERT_Y` 값을 패널 방향에 맞게 조정합니다. `T_CS`가 GPIO 7이 아닌 모듈은
`TOUCH_CS` 값을 실제 배선 번호로 변경해야 합니다.

=======
//
앞으로 해야할 것

하드웨어

1. 로터리 엔코더 납 땜 및 배선
2. 터치 방식 기능 구현

소프트웨어

1. csv(데이터 파일)로 재고 등 매장 혹은 사업장 db는 임시 파일로 만들어서 설명할 수 있게 해야함.
상품 인식 및 수하물 관련 정보는 gemni api가 판단. 
2. git issue에 플로우 차트 및 개발 시 발생했던 어려움들  docs에 기록


추가적 구현 :
카메라가 촬영 버튼을 누르면 preview로 카메라가 인식하고 있는지 볼 수 있게 함.
>>>>>>> b21c63c (Revise README with project updates and next steps)

문서 반영 및 수정 사항 : 
제출용 엑셀 인적사항 반영하기.

## CSV 상품 데이터

`inventory.csv`는 다음 열을 사용합니다.

현재 `retail_product_inventory_large.csv`는 다음 열을 사용합니다.

`product_id,product_name,category,price,stock_quantity,location`

Gemini가 인식한 상품명과 `product_name`을 비교해 일치하는 행을 찾고, 매장/재고/
위치/설명을 결과 화면에 표시합니다. 다른 파일을 사용하려면 Raspberry Pi에서
`INVENTORY_CSV=/경로/파일.csv python3 main.py`처럼 실행합니다.

## Raspberry Pi 부팅 자동 실행

Raspberry Pi에서 프로젝트 폴더로 이동한 뒤 다음 명령을 한 번 실행합니다.

```bash
sudo bash install_autostart.sh
```

그러면 전원이 켜지고 네트워크가 준비된 뒤 `main.py`가 자동 실행되어 LCD가
초기화됩니다. Gemini API 키는 서비스 사용자 기준으로 생성된 파일에 저장합니다.

```bash
nano ~/.config/info-bridge.env
GEMINI_API_KEY=발급받은_키
```

서비스 확인 및 로그:

```bash
sudo systemctl status info-bridge.service
sudo journalctl -u info-bridge.service -f
```

서비스를 중지하려면 `sudo systemctl disable --now info-bridge.service`를 실행합니다.



