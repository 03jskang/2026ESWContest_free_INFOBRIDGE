"""
touch_module.py
ILI9486 모듈에 흔히 함께 사용되는 XPT2046 저항막 터치 입력.

기본 배선:
    T_IRQ -> GPIO26, T_CS -> GPIO7
    T_CLK -> GPIO11, T_DIN -> GPIO10, T_DO -> GPIO9
"""

import RPi.GPIO as GPIO
import spidev

TOUCH_IRQ = 26
TOUCH_CS = 7
TOUCH_SPI_BUS = 0
TOUCH_SPI_DEVICE = 1

# 화면 방향/패널에 따라 보정해야 하는 원시 좌표 범위
RAW_X_MIN = 200
RAW_X_MAX = 3800
RAW_Y_MIN = 200
RAW_Y_MAX = 3800
SWAP_XY = False
INVERT_X = False
INVERT_Y = False

_spi = None


def init_touch():
    """터치 IRQ와 SPI 채널을 초기화한다."""
    global _spi

    GPIO.setup(TOUCH_IRQ, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(TOUCH_CS, GPIO.OUT, initial=GPIO.HIGH)

    _spi = spidev.SpiDev()
    _spi.open(TOUCH_SPI_BUS, TOUCH_SPI_DEVICE)
    _spi.max_speed_hz = 1_000_000
    _spi.mode = 0
    _spi.no_cs = True


def _read_axis(command: int) -> int:
    GPIO.output(TOUCH_CS, GPIO.LOW)
    response = _spi.xfer2([command, 0, 0])
    GPIO.output(TOUCH_CS, GPIO.HIGH)
    return ((response[1] << 8) | response[2]) >> 3


def _scale(value: int, minimum: int, maximum: int, size: int) -> int:
    value = max(minimum, min(value, maximum))
    return round((value - minimum) * (size - 1) / (maximum - minimum))


def read_touch_point(screen_width: int, screen_height: int):
    """현재 눌린 터치의 화면 좌표를 반환하고, 아니면 None을 반환한다."""
    if _spi is None or GPIO.input(TOUCH_IRQ):
        return None

    raw_x = sum(_read_axis(0xD0) for _ in range(3)) // 3
    raw_y = sum(_read_axis(0x90) for _ in range(3)) // 3
    x = _scale(raw_x, RAW_X_MIN, RAW_X_MAX, screen_width)
    y = _scale(raw_y, RAW_Y_MIN, RAW_Y_MAX, screen_height)

    if SWAP_XY:
        x, y = y, x
    if INVERT_X:
        x = screen_width - 1 - x
    if INVERT_Y:
        y = screen_height - 1 - y
    return x, y


def close_touch():
    """터치 SPI 장치를 닫는다."""
    global _spi
    if _spi is not None:
        _spi.close()
        _spi = None
