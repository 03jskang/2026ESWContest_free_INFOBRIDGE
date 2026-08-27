import os

import spidev
import RPi.GPIO as GPIO
import time
from PIL import Image

DC = 24
RST = 25
CS = 8
COLOR_ORDER = os.environ.get("LCD_COLOR_ORDER", "RGB").upper()
MADCTL_COLOR = 0x28 if COLOR_ORDER == "BGR" else 0x20

WIDTH = 480
HEIGHT = 320

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(DC, GPIO.OUT)
GPIO.setup(RST, GPIO.OUT)
GPIO.setup(CS, GPIO.OUT)
GPIO.output(CS, GPIO.HIGH)

spi = spidev.SpiDev()
spi.open(0, 0)
# 프레임 전송 지연을 줄인다. 화면이 깨지거나 불안정하면 8000000으로 낮춘다.
spi.max_speed_hz = 32000000
spi.mode = 0
spi.no_cs = True  # 하드웨어 자동 CS 끄고 GPIO로 직접 제어

def send_cmd(cmd):
    GPIO.output(CS, GPIO.LOW)
    GPIO.output(DC, GPIO.LOW)
    spi.writebytes([cmd])
    GPIO.output(CS, GPIO.HIGH)

def send_data(data):
    GPIO.output(CS, GPIO.LOW)
    GPIO.output(DC, GPIO.HIGH)
    if isinstance(data, int):
        data = [data]
    spi.writebytes(data)
    GPIO.output(CS, GPIO.HIGH)

def reset():
    GPIO.output(RST, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(RST, GPIO.LOW)
    time.sleep(0.05)
    GPIO.output(RST, GPIO.HIGH)
    time.sleep(0.15)

def init():
    reset()

    send_cmd(0x01)
    time.sleep(0.15)

    send_cmd(0xF2)
    send_data([0x18, 0xA3, 0x12, 0x02, 0xB2, 0x12, 0xFF, 0x10, 0x00])

    send_cmd(0xF1)
    send_data([0x36, 0x04, 0x00, 0x3C, 0x0F, 0x8F])

    send_cmd(0xF8)
    send_data([0x21, 0x04])

    send_cmd(0xF9)
    send_data([0x00, 0x08])

    send_cmd(0xC0)
    send_data([0x0D, 0x0D])

    send_cmd(0xC1)
    send_data([0x43, 0x00])

    send_cmd(0xC2)
    send_data([0x00])

    send_cmd(0xC5)
    send_data([0x00, 0x48, 0x00, 0x48])

    send_cmd(0xB6)
    send_data([0x00, 0x22, 0x3B])

    send_cmd(0xB1)
    send_data([0xC0, 0x11])

    send_cmd(0xB4)
    send_data([0x02])

    send_cmd(0xE0)
    send_data([0x0F, 0x24, 0x1C, 0x0A, 0x0F, 0x08, 0x43, 0x88,
                0x32, 0x0F, 0x10, 0x06, 0x0F, 0x07, 0x00])

    send_cmd(0xE1)
    send_data([0x0F, 0x38, 0x30, 0x09, 0x0F, 0x0F, 0x4F, 0x68,
                0x36, 0x08, 0x10, 0x03, 0x21, 0x04, 0x00])

    send_cmd(0x3A)
    send_data(0x55)

    send_cmd(0x36)
    # 이 패널은 BGR 순서가 기본이다. RGB 패널이면 LCD_COLOR_ORDER=RGB를 사용한다.
    send_data(MADCTL_COLOR)

    # 색상 반전 상태를 명시적으로 해제한다. 반전 상태에서는 파랑이 노랑으로 보인다.
    send_cmd(0x20)

    send_cmd(0x11)
    time.sleep(0.15)
    send_cmd(0x29)
    time.sleep(0.05)

def set_window(x0, y0, x1, y1):
    send_cmd(0x2A)
    send_data([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF])
    send_cmd(0x2B)
    send_data([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF])
    send_cmd(0x2C)

def display_image(img):
    img = img.resize((WIDTH, HEIGHT)).convert("RGB")
    pixels = img.load()
    set_window(0, 0, WIDTH - 1, HEIGHT - 1)

    buf = []
    CHUNK = 4000

    GPIO.output(CS, GPIO.LOW)
    GPIO.output(DC, GPIO.HIGH)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r, g, b = pixels[x, y]
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buf.append(rgb565 >> 8)
            buf.append(rgb565 & 0xFF)
            if len(buf) >= CHUNK:
                spi.writebytes(buf)
                buf = []
    if buf:
        spi.writebytes(buf)
    GPIO.output(CS, GPIO.HIGH)


def close():
    """LCD SPI와 이 드라이버가 사용하는 GPIO를 해제한다."""
    if spi:
        spi.close()
    GPIO.cleanup([DC, RST, CS])

if __name__ == "__main__":
    print("1. init 시작")
    init()
    print("2. init 완료, 이미지 생성")
    img = Image.new("RGB", (WIDTH, HEIGHT), (255, 0, 0))
    print("3. display_image 시작")
    display_image(img)
    print("4. 빨간 화면이 떴으면 성공!")
