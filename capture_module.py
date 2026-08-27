"""
capture_module.py
Picamera2 프리뷰 표시와 정지 이미지 촬영/전처리를 담당한다.
"""

import time
from pathlib import Path
from threading import Lock

from PIL import Image, ImageOps
from picamera2 import Picamera2

PREVIEW_CAMERA_SIZE = (640, 480)
PREVIEW_SIZE = (480, 320)
STILL_CAMERA_SIZE = (1536, 864)
CAPTURE_PATH = Path("captured.jpg")
PROCESSED_PATH = Path("captured_processed.jpg")
FLIP_CAMERA_VERTICAL = True

_camera = None
_latest_frame = None
_frame_lock = Lock()


def _ensure_camera():
    global _camera

    if _camera is None:
        with _frame_lock:
            global _latest_frame
            _latest_frame = None
        _camera = Picamera2()
        preview_config = _camera.create_preview_configuration(
            main={"size": PREVIEW_CAMERA_SIZE, "format": "RGB888"},
            buffer_count=4,
        )
        _camera.configure(preview_config)
        _camera.start()
    return _camera


def _update_preview_frame():
    """카메라의 최신 프레임을 LCD 렌더링용 PIL 이미지로 저장한다."""
    frame = _ensure_camera().capture_array("main")
    image = Image.fromarray(frame).convert("RGB")
    if FLIP_CAMERA_VERTICAL:
        image = ImageOps.flip(image)
    with _frame_lock:
        global _latest_frame
        _latest_frame = image


def get_preview_frame():
    """메인 화면에서 사용할 최신 프리뷰 프레임을 반환한다."""
    with _frame_lock:
        return _latest_frame.copy() if _latest_frame is not None else None


def capture_and_preprocess(preview_seconds: float = 2.0) -> str:
    """프리뷰를 표시한 뒤 촬영하고, AI 전송용 이미지 경로를 반환한다."""
    global _camera

    camera = _ensure_camera()
    deadline = time.monotonic() + preview_seconds

    while time.monotonic() < deadline:
        _update_preview_frame()

    try:
        still_config = camera.create_still_configuration(
            main={"size": STILL_CAMERA_SIZE, "format": "RGB888"},
            buffer_count=2,
        )
        camera.switch_mode_and_capture_file(still_config, str(CAPTURE_PATH))
    finally:
        try:
            camera.stop()
        finally:
            camera.close()
            _camera = None

    with Image.open(CAPTURE_PATH) as image:
        image = image.convert("RGB")
        if FLIP_CAMERA_VERTICAL:
            image = ImageOps.flip(image)
        processed = ImageOps.fit(image, PREVIEW_SIZE)
        processed.save(PROCESSED_PATH, quality=95)

    return str(PROCESSED_PATH)


def close_camera():
    """예외나 프로그램 종료 시 카메라를 정리한다."""
    global _camera
    if _camera is not None:
        try:
            _camera.stop()
        finally:
            _camera.close()
        _camera = None
