"""
test_camera.py
카메라가 라즈베리파이에서 제대로 인식되고 촬영되는지 확인하는 테스트 스크립트.

실행 방법 (라즈베리파이 터미널에서):
    cd ~/info-bridge
    source venv/bin/activate
    python3 test_camera.py

정상 동작하면 같은 폴더에 test.jpg 파일이 생성됩니다.
"""

from picamera2 import Picamera2
import time

def main():
    picam2 = Picamera2()

    # 정지 이미지용 설정 생성
    config = picam2.create_still_configuration()
    picam2.configure(config)

    picam2.start()
    print("카메라 시작됨. 2초간 노출/오토포커스 안정화 대기...")
    time.sleep(2)  # 카메라가 밝기/초점을 맞출 시간을 줌

    picam2.capture_file("test.jpg")
    print("촬영 완료: test.jpg 저장됨")

    picam2.stop()

if __name__ == "__main__":
    main()
