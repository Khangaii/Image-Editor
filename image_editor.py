# image_editor.py

# Flask 라이브러리
from flask import Flask, render_template, templating, jsonify, json

# 라스베리 파이 라이브러리
import RPi.GPIO as GPIO

# SPI 통신 라이브러리
import spidev

# OLED 조정 라이브러리
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
from board import SCL, SDA
import adafruit_ssd1306

# OpenCV 라이브러리
import cv2

# numpy 라이브러리
import numpy as np

# 수학 라이브러리
import math

# 시간 조정 라이브러리
import time

# 카메라 읽기 조절에 필요한 라이브러리
import queue, threading

# 키보드 입력 인식 라이브러리
from pynput import keyboard

# 운영체제에 관한 라이브러리
# 디렉토리 안의 파일을 가져오려고 씀
import os

# cv2 윈도우의 이름
WINDOW_NAME = "Editz"

# ASCII 코드
ENTER = 13
ESC = 27
SPACE = 32

OLED_DISPLAY = 0x3c        # 붓 상태와 설정 선택 보여주는 OLED 주소

BUTTON_DRAW = 26            # 그냥 그리기
BUTTON_LINE = 19            # 직선 그리기
BUTTON_RECT = 13            # 직사각형 그리기
BUTTON_CIRC = 6             # 원 그리기
BUTTON_ERASE = 5            # 지우기

BUTTON_SIZE = 22            # 붓 크기 설정
BUTTON_COLOR = 27           # 붓 색깔 설정
BUTTON_TRANSP = 17          # 붓 불투명도 설정

RGB_RED = 18                # RGB LED 붉은색
RGB_GREEN = 15              # RGB LED 추록색
RGB_BLUE = 14               # RGB LED 파란색

BUZZER_PIN = 21             # 피에조 부저 핀

# GPIO.OUT으로 설정할 핀
OUT_PIN = [RGB_RED, RGB_GREEN, RGB_BLUE,
           BUZZER_PIN]

# GPIO.IN으로 설정할 핀
IN_PIN = []

# GPIO.IN이고 GPIO.PUD_UP으로 설정할 핀
PULL_UP = []
    
# GPIO.IN이고 GPIO.PUD_DOWN으로 설정할 핀
PULL_DOWN = [BUTTON_DRAW, BUTTON_LINE, BUTTON_RECT, BUTTON_CIRC, BUTTON_ERASE,
             BUTTON_SIZE, BUTTON_COLOR, BUTTON_TRANSP]  


# 찍은 사진
picture = None
# 사진을 찍었는지 불 변수
picture_isTaken = None
# 사진 찍고 필터 더한 후 에디터의 배경으로 쓸 이미지
background = None
# 최대 몇개의 프레임을 저장할지
frame_number = 5
# 최대 frame_number개의 프레임을 저장한 배열
frames = [None] * frame_number
# cv2.imshow 윈도우에 보여주는 프레임
current_frame = None
# 이미지의 이름
image_name = None

# 라스베리 파이의 BCM 핀을 쓴다
GPIO.setmode(GPIO.BCM)

# SPI 인스턴스 생성
spi = spidev.SpiDev()

# SPI 통신 시작 => bus:0, dev:0
spi.open(0, 0)

# SPI 통신 속도 설정
spi.max_speed_hz = 100000

# OLED reset 핀 초기화
RESET_PIN = digitalio.DigitalInOut(board.D4)

# I2C OLED 초기화
i2c = board.I2C()

# OLED
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=OLED_DISPLAY, reset=RESET_PIN)

# OLED 폰트를 수입하기
DejaVuSans = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)

# 붓의 상태
# 0: 붓
# 1: 선
# 2: 빈 직사각형    3: 가득 찬 직사각형
# 4: 빈 원          5: 가득 찬 원
# 6: 원형 지우개     7: 직사각형 지우개
brush_type = 0
# 설정의 선택
# 0: 크기
# 1: 색조  2: 채도  3: 명도
# 4: 불투명도
setting_type = 0

# 붓의 크기 초기화
size = 5

# 마우스 현재 위치
x0 = -1
y0 = -1

# 마우스의 처음 위치
x1 = -1
y1 = -1

# 마우스의 flag
mouse_flags = None

# 마우스의 param
mouse_param = None

# 색깔 초기화
hue = 0
saturation = 100
lightness = 50
HSL_color = (hue, saturation, lightness)

red = 0
green = 0
blue = 0
RGB_color = (red, green, blue)

# RGB LED 조절
pwm_red = None
pwm_green = None
pwm_blue = None

# 불투명도
alpha = 1.0

# 카메라 장치 객체
cap = None

# 키보드 이벤트 인식 객체
listener = None

# 이미지를 편집했는지의 불
image_edited = False

# 여러 버튼의 값 입력 저장
button_input = [None] * 8

# 가변저항의 값
potentiometer = None

# oled로 출력할 그림
LOGO = [
    (3, [7, 8]),
    (4, [6, 7, 8, 9]),
    (5, [6, 7, 8, 9]),
    (6, [7, 8]),
    (8, [5, 6, 7, 8, 9]),
    (9, [4, 5, 6, 7, 8, 9, 10]),
    (10, [4, 5, 8, 9, 10]),
    (11, [5, 8, 9, 10]),
    (12, [7, 8, 9, 29, 30, 31, 32]),
    (13, [7, 8, 17, 18, 23, 24, 28, 29, 30, 31, 32, 33]),
    (14, [6, 7, 16, 17, 18, 19, 22, 23, 24, 25, 28, 33, 34, 41, 42, 46, 47, 48, 49]),
    (15, [6, 7, 15, 16, 17, 19, 20, 21, 22, 25, 26, 33, 34, 38, 39, 40, 41, 42, 43, 45, 46, 50]),
    (16, [5, 6, 7, 15, 16, 19, 20, 21, 25, 26, 29, 30, 31, 32, 33, 34, 36, 37, 41, 42, 43, 45, 50]),
    (17, [5, 6, 15, 16, 20, 21, 25, 26, 28, 29, 30, 33, 34, 36, 42, 45, 47, 48, 49, 52, 53]),
    (18, [5, 6, 7, 10, 11, 12, 15, 16, 20, 21, 25, 26, 28, 29, 33, 34, 36, 37, 41, 42, 45, 46, 51, 52, 53]),
    (19, [5, 6, 7, 8, 9, 10, 11, 12, 15, 16, 20, 21, 25, 26, 28, 29, 33, 34, 37, 38, 39, 40, 41, 45, 46, 47, 50, 51, 52]),
    (20, [7, 8, 9, 10, 11, 15, 20, 21, 25, 29, 30, 31, 32, 33, 35, 38, 39, 46, 47, 48, 49, 50, 51]),
    (21, [38, 39, 40, 41]),
    (22, [36, 37, 38, 40, 41]),
    (23, [35, 41, 42]),
    (24, [35, 36, 41, 42]),
    (25, [36, 37, 38, 39, 40, 41]),
    (26, [37, 38, 39, 40]),
    (32, [8, 9, 10, 11, 12, 13]),
    (33, [6, 7, 8, 9, 10, 11, 12, 13, 14, 15]),
    (34, [5, 6, 7, 13, 14, 15, 16]),
    (35, [4, 5, 6, 15, 16, 17]),
    (36, [4, 5, 16, 17]),
    (37, [3, 4, 5, 16, 17]),
    (38, [3, 4, 15, 16, 17]),
    (39, [3, 4, 13, 14, 15, 16]),
    (40, [3, 4, 9, 10, 11, 12, 13, 14, 41]),
    (41, [3, 4, 5, 9, 10, 11, 12, 23, 32, 33, 34, 41]),
    (42, [3, 4, 5, 22, 23, 24, 27, 28, 32, 33, 34, 41]),
    (43, [4, 5, 6, 21, 22, 23, 24, 27, 28, 32, 33, 34, 40, 41]),
    (44, [4, 6, 7, 20, 21, 22, 23, 27, 28, 40, 41, 48, 49, 55, 59, 60, 61]),
    (45, [5, 6, 7, 8, 9, 19, 20, 21, 22, 23, 27, 28, 31, 32, 33, 34, 39, 40, 41, 47, 48, 49, 50, 51, 54, 56, 58, 59, 60, 61, 62]),
    (46, [6, 7, 8, 9, 10, 11, 18, 19, 20, 21, 22, 27, 28, 30, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 44, 47, 48, 52, 54, 56, 57, 58, 59, 62]),
    (47, [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 27, 28, 33, 34, 35, 40, 41, 46, 47, 52, 53, 57, 58]),
    (48, [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 27, 28, 32, 33, 34, 40, 41, 46, 47, 53, 57, 58]),
    (49, [13, 14, 15, 16, 17, 22, 23, 24, 25, 27, 28, 32, 33, 40, 41, 46, 53, 57, 58]),
    (50, [21, 22, 25, 26, 27, 28, 31, 32, 33, 39, 40, 46, 52, 53, 56, 57]),
    (51, [20, 21, 26, 27, 28, 31, 32, 39, 40, 46, 47, 52, 53, 56, 57]),
    (52, [19, 20, 26, 27, 28, 30, 31, 32, 39, 40, 45, 46, 47, 51, 52, 53, 56, 57]),
    (53, [19, 20, 26, 27, 28, 30, 31, 39, 40, 41, 45, 46, 47, 48, 49, 50, 51, 52, 56]),
    (54, [19, 20, 25, 26, 27, 28, 30, 31, 35, 36, 39, 40, 41, 44, 45, 46, 49, 50, 51, 55]),
    (55, [19, 20, 21, 23, 24, 25, 27, 28, 30, 31, 32, 34, 35, 36, 40, 41, 42, 43, 44, 45, 71, 74, 86, 87, 88, 101, 120]),
    (56, [20, 21, 22, 23, 24, 27, 28, 31, 32, 33, 34, 35, 41, 42, 43, 44, 71, 74, 85, 101, 120]),
    (57, [32, 33, 34, 71, 74, 85, 101, 116, 117, 119]),
    (58, [71, 72, 73, 74, 86, 87, 101, 115, 118, 119]),
    (59, [71, 74, 88, 101, 115, 118]),
    (60, [71, 74, 88, 101, 116, 117, 119]),
    (61, [71, 74, 85, 86, 87, 101, 102, 103, 104, 120, 121])
]

# oled로 출력할 그림2
brush_type_free = [
    (8, [76, 77]),
    (9, [74, 75, 76, 77]),
    (10, [73, 74, 77, 89, 90, 91, 92, 93]),
    (11, [72, 73, 77, 86, 87, 88, 89, 93]),
    (12, [76, 86, 93]),
    (13, [76, 84, 85, 93]),
    (14, [75, 83, 84, 93]),
    (15, [74, 75, 82, 83, 93, 109, 110, 111, 112]),
    (16, [74, 79, 80, 81, 92, 107, 108, 113]),
    (17, [73, 78, 79, 91, 106, 107, 113]),
    (18, [73, 76, 77, 78, 91, 105, 106, 113]),
    (19, [73, 74, 75, 76, 90, 105, 113]),
    (20, [90, 104, 113]),
    (21, [90, 103, 113]),
    (22, [89, 90, 101, 102, 113, 114]),
    (23, [89, 100, 101, 114]),
    (24, [89, 99, 114, 115]),
    (25, [89, 96, 97, 98, 116]),
    (26, [89, 90, 91, 92, 93, 94, 95, 96])
]

#-------------------------------------------------------------------------------------------------------------------------------------
# 함수를 여기 만들 것이다

# cap.read() 할 때 최대의 프레임을 가지도록 하는 클라스
class VideoCapture:

  def __init__(self, name):
    self.cap = cv2.VideoCapture(name)
    self.q = queue.Queue()
    self.r = queue.Queue()
    t = threading.Thread(target=self._reader)
    t.daemon = True
    t.start()

  # read frames as soon as they are available, keeping only most recent one
  def _reader(self):
    while True:
      ret, frame = self.cap.read()
      if not self.r.empty():
        try:
          self.r.get_nowait()   # discard previous (unprocessed) frame
        except queue.Empty:
          pass
      self.r.put(ret)
      if not self.q.empty():
        try:
          self.q.get_nowait()   # discard previous (unprocessed) frame
        except queue.Empty:
          pass
      self.q.put(frame)

  def read(self):
    return (self.r.get(), self.q.get())

  def isOpened(self):
    return self.cap.isOpened()

  def release(self):
    self.cap.release()

# 키보드 이벤트 인식 함수
def on_press(key):
  global brush_type, setting_type

  if key == keyboard.Key.a:
    brush_type = 0

    draw_oled()

  elif key == keyboard.Key.s:
    brush_type = 1

    draw_oled()

  elif key == keyboard.Key.d:
    if brush_type == 2:
      brush_type = 3
    else:
      brush_type = 2
    
    draw_oled()

  elif key == keyboard.Key.f:
    if brush_type == 4:
      brush_type = 5
    else:
      brush_type = 4
    
    draw_oled()

  elif key == keyboard.Key.g:
    brush_type = 6
    
    draw_oled()

  elif key == keyboard.Key.j:
    setting_type = 0

  elif key == keyboard.Key.k:
    if brush_type in (1, 2, 3):
      setting_type = setting_type%3 + 1
    else:
      setting_type = 1

  elif key == keyboard.Key.l:
    setting_type = 4


# 0~7까지 8개의 채널에서 SPI 데이터 읽기
def analog_read(channel):
  # [byte_1, byte_2, byte_3]
  # byte_2 : channel config (channel 0) (+8) -> 0000 1000 -> 1000 0000
  ret = spi.xfer2([1,  (8 +  channel) << 4, 0])
  adc_out = ((ret[1] & 3) << 8) + ret[2]
  return adc_out


# 핀의 상태를 초기화하기
def initialize_pin():
  for pin in OUT_PIN:
    GPIO.setup(pin, GPIO.OUT)

  for pin in IN_PIN:
    GPIO.setup(pin, GPIO.IN)

  # for pin in PULL_UP:
  #   GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
  
  for pin in PULL_DOWN:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def input_all():
  global button_input, potentiometer

  button_input[0] = GPIO.input(BUTTON_DRAW)
  button_input[1] = GPIO.input(BUTTON_LINE)
  button_input[2] = GPIO.input(BUTTON_RECT)
  button_input[3] = GPIO.input(BUTTON_CIRC)
  button_input[4] = GPIO.input(BUTTON_ERASE)
  button_input[5] = GPIO.input(BUTTON_SIZE)
  button_input[6] = GPIO.input(BUTTON_COLOR)
  button_input[7] = GPIO.input(BUTTON_TRANSP)

  potentiometer = analog_read(0)

# HSL 색깔에서 RGB로 바꾸기

def clamp(value, min_value, max_value):
	return max(min_value, min(max_value, value))

def saturate(value):
	return clamp(value, 0.0, 1.0)

def hue_to_rgb(h):
	r = abs(h * 6.0 - 3.0) - 1.0
	g = 2.0 - abs(h * 6.0 - 2.0)
	b = 2.0 - abs(h * 6.0 - 4.0)
	return saturate(r), saturate(g), saturate(b)

def HSL_to_RGB():
  global hue, saturation, lightness, red, green, blue, RGB_color

  h = hue/360.0
  s = saturation/100.0
  l = lightness/100.0

  r, g, b = hue_to_rgb(h)
  c = (1.0 - abs(2.0 * l - 1.0)) * s
  r = (r - 0.5) * c + l
  g = (g - 0.5) * c + l
  b = (b - 0.5) * c + l

  red = int(r*255)
  green = int(g*255)
  blue = int(b*255)

  RGB_color = (red, green, blue)

def set_rgb_led():
  global pwm_red, pwm_green, pwm_blue, red, green, blue

  pwm_red.ChangeDutyCycle(int(red*100/255))
  pwm_green.ChangeDutyCycle(int(green*100/255))
  pwm_blue.ChangeDutyCycle(int(blue*100/255))

# current_frame을 frames에 저장하기
def append_frame():
  global current_frame, frames

  for i in range(1, frame_number-1):
    if frames[i] is None:
      continue
    frames[i-1] = frames[i].copy()

  frames[frame_number-1] = current_frame.copy()

# 마우스 인식 없애기
def no_mouse(event, x, y, flags, param):
  pass

# 마우스 동작
def mouse_event(event, x, y, flags, param):
  global current_frame, frames, RGB_color, HSL_color, x0, y0, x1, y1, mouse_flags, mouse_param, image_edited

  # 마우스의 상태 초기화
  x0 = x
  y0 = y
  mouse_flags = flags
  mouse_param = param

  roi = None

  # 왼쪽 마우스 버튼이 눌러 있을 때
  if event == cv2.EVENT_MOUSEMOVE and flags != cv2.EVENT_FLAG_LBUTTON:
    if brush_type == 6:
      current_frame = frames[frame_number-1].copy()
      cv2.rectangle(current_frame, (x-size, y-size), (x+size, y+size), (255, 255, 255), -1)

    else:
      current_frame = frames[frame_number-1].copy()
      cv2.circle(current_frame, (x, y), size, RGB_color, -1)

  # 마우스가 움직일 때
  elif event == cv2.EVENT_MOUSEMOVE:
    if brush_type == 0:
      cv2.circle(current_frame, (x, y), size, RGB_color, -1)

    elif brush_type == 1:
      current_frame = frames[frame_number-1].copy()
      cv2.line(current_frame, (x1, y1), (x, y), RGB_color, size*2)

    elif brush_type == 2:
      current_frame = frames[frame_number-1].copy()
      cv2.rectangle(current_frame, (x1, y1), (x, y), RGB_color, size*2)

    elif brush_type == 3:
      current_frame = frames[frame_number-1].copy()
      cv2.rectangle(current_frame, (x1, y1), (x, y), RGB_color, -1)

    elif brush_type == 4:
      current_frame = frames[frame_number-1].copy()
      cv2.ellipse(current_frame, (int((x+x1)/2), int((y+y1)/2)), (abs(int((x-x1)/2)), abs(int((y-y1)/2))), 0.0, 0.0, 360.0, RGB_color, -1)

    elif brush_type == 5:
      current_frame = frames[frame_number-1].copy()
      cv2.ellipse(current_frame, (int((x+x1)/2), int((y+y1)/2)), (abs(int((x-x1)/2)), abs(int((y-y1)/2))), 0.0, 0.0, 360.0, RGB_color, size*2)

    elif brush_type == 6:
      roi = background[y-size : y+size, x-size : x+size]
      current_frame[y-size : y+size, x-size : x+size] = roi.copy()

  # 왼쪽 마우스 버튼 누를 때
  elif event == cv2.EVENT_LBUTTONDOWN:
    current_frame = frames[frame_number-1].copy()

    if brush_type == 0:
      cv2.circle(current_frame, (x, y), size, RGB_color, -1)

    elif brush_type in (1, 2, 3, 4, 5):
      x1, y1 = x, y

    elif brush_type == 6:
      roi = background[y-size : y+size, x-size : x+size]
      current_frame[y-size : y+size, x-size : x+size] = roi.copy()

    image_edited = True

  # 왼쪽 마우스 버튼이 눌리지 않았을 때
  elif event == cv2.EVENT_LBUTTONUP:
    append_frame()
    image_edited = False

  cv2.imshow(WINDOW_NAME, current_frame)


# 사진을 찍기
# return -1: 오류, 0: 안 찍었다, 1: 성공
def take_picture():
  global picture, picture_isTaken, background, frames, current_frame, image_name, cap

  # cv2 윈도우 만들기
  print("making window")
  cv2.namedWindow(WINDOW_NAME)
  print("window made")

  # 카메라의 시각을 출력하기
  while True:
    ret, frame = cap.read()

    if not ret:
      print("camera stopped working") 
      return -1
    
    cv2.imshow(WINDOW_NAME, frame)

    key = cv2.waitKey(10)

    # Enter이나 Space누르면 사진 찍기
    if key == 13 or key == 32:
      picture = frame.copy()
      picture_isTaken = True

      print("picture taken")

      # 마리오 코인 얻을 때의 시엠송
      buzzer.ChangeFrequency(988)
      buzzer.start(50)
      time.sleep(0.075)
      buzzer.ChangeFrequency(1319)
      time.sleep(0.525)
      buzzer.stop()

      break
  
    # Esc누르거나 창을 닫으면 찍기를 취소하기
    elif key == 27 or cv2.getWindowProperty(WINDOW_NAME, 0) < 0:
      break

  # 사진을 안 찍었으면 cv2윈도우를 삭제하고 0을 반환한다
  if not picture_isTaken:
    cv2.destroyAllWindows()
    return 0
  
  return 1


# 이미지에다가 필터 붙이기
def add_filter():
  global picture, picture_isTaken, background, frames, current_frame, image_name

  # 임시의 코드!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  background = picture.copy()

  frames[frame_number-1] = background.copy()

  current_frame = frames[frame_number-1].copy()

  return 1


# 이미지를 편집하기
def edit_image():
  global picture, picture_isTaken, background, frames, current_frame, image_name, brush_type, setting_type, size, listener, button_input, potentiometer, HSL_color, hue, saturation, lightness, alpha

  # 필터 추가하기
  ret = add_filter()

  if ret <= 0:
    return ret
  
  # 키보드 이벤트 인식 시작하기
  listener.start()

  # 마우스 이벤트 인식 시작하기
  cv2.setMouseCallback(WINDOW_NAME, mouse_event)

  # 몇 millisecond 지났는지 저장
  ms_passed = 0

  # 최대 눌른 버튼 수 저장
  last_pressed = -1

  # 지금 누르는 중인지 저장
  mid_press = False

  # 지난 루프의 가변 저항 값
  last_potentiometer = -1

  # 브레드보드의 작용
  while True:
    input_all()

    # 버튼에 따라 설정
    if button_input[0] == GPIO.HIGH:
      mid_press = True
      brush_type = 0
      last_pressed = 0

      draw_oled()

    elif button_input[1] == GPIO.HIGH:
      mid_press = True
      brush_type = 1
      last_pressed = 1

      draw_oled()

    elif button_input[2] == GPIO.HIGH:
      if last_pressed == 2:
        if not mid_press:
          mid_press = True
          if brush_type == 2:
            brush_type = 3
          else:
            brush_type = 2
      else:
        mid_press = True
        last_pressed = 2
        brush_type = 2
      
      draw_oled()

    elif button_input[3] == GPIO.HIGH:
      if last_pressed == 3:
        if not mid_press:
          mid_press = True
          if brush_type == 4:
            brush_type = 5
          else:
            brush_type = 4
      else:
        mid_press = True
        last_pressed = 3
        brush_type = 4
      
      draw_oled()

    elif button_input[4] == GPIO.HIGH:
      mid_press = True
      brush_type = 6
      last_pressed = 4

      draw_oled()


    elif button_input[5] == GPIO.HIGH:
      mid_press = True
      setting_type = 0
      last_pressed = 5


    elif button_input[6] == GPIO.HIGH:
      if last_pressed == 6:
        if not mid_press:
          mid_press = True
          setting_type = setting_type%3 + 1
      else:
        mid_press = True
        last_pressed = 6
        setting_type = 1

    elif button_input[7] == GPIO.HIGH:
      mid_press = True
      setting_type = 4
      last_pressed = 7
    
    else:
      mid_press = False

    # 붓 상태 설정
    if abs(potentiometer-last_potentiometer) > 50:
      if setting_type == 0:
        size = int(((potentiometer+1)*5)/256)
      
      if setting_type == 1:
        hue = int(((potentiometer)*360)/1023)

        # HSL 초기화
        HSL_color = (hue, saturation, lightness)
        # HSL -> RGB
        HSL_to_RGB()
        set_rgb_led()

      if setting_type == 2:
        saturation = int(((potentiometer)*100)/1023)

        # HSL 초기화
        HSL_color = (hue, saturation, lightness)
        # HSL -> RGB
        HSL_to_RGB()
        set_rgb_led()

      if setting_type == 3:        
        lightness = int(((potentiometer)*100)/1023)
        
        # HSL 초기화
        HSL_color = (hue, saturation, lightness)
        # HSL -> RGB
        HSL_to_RGB()
        set_rgb_led()

      if setting_type == 4:
        alpha = float(((potentiometer))/1023)

      last_potentiometer = potentiometer

      draw_oled()
    
    mouse_event(cv2.EVENT_MOUSEMOVE, x0, y0, mouse_flags, mouse_param)

    key = cv2.waitKey(10)
    ms_passed += 10

    # ESC 누를 때 멈추기
    if key == 27:
      ret = 1
      break

    # 창을 닫을 때 멈추기
    elif cv2.getWindowProperty(WINDOW_NAME, 0) < 0:
      ret = 0
      break
  
  # 키보드 이벤트 인식 멈추기
  print("listener stopping")
  listener.stop()
  print("listener stopped")

  # 마우스 이벤트 인식 멈추기
  print("retracting mouse call back")
  cv2.setMouseCallback(WINDOW_NAME, no_mouse)
  print("mouse call back retracted")

  return ret

# 이미지의 이름 입력받기
def get_name():
  global picture, picture_isTaken, background, frames, current_frame, image_name

  # 임시의 코드!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  image_name = input("input name: ")


  return 1

# oled에 hsl, alpha, brush_type출력
def draw_oled():
  global hue, saturation, lightness, alpha, brush_type

  for x in range(66, 127):
    for y in range(2, 36):
      oled.pixel(x, y, 0)
        
  for x in range(65, 127):
    for y in range(38, 54):
      oled.pixel(x, y, 0)

  oled.show()

  for i in range(0, int(15*(hue/360))):
    oled.pixel(72, 53-i, color=color)
    oled.pixel(73, 53-i, color=color)

  for i in range(0, int(15*(saturation/100))):
    oled.pixel(86, 53-i, color=color)
    oled.pixel(87, 53-i, color=color)

  for i in range(0, int(15*(lightness/100))):
    oled.pixel(102, 53-i, color=color)
    oled.pixel(103, 53-i, color=color)

  for i in range(0, int(15*(alpha))):
    oled.pixel(117, 53-i, color=color)
    oled.pixel(118, 53-i, color=color)

  if brush_type == 0:
    for y, x in brush_type_free:
      for i in x:
        oled.pixel(i+1, y, color=color)
  elif brush_type == 1:
    oled.line(70, 32, 121, 7, color=color)
  elif brush_type == 2:
    oled.rect(70, 7, 52, 25, color=color)
  elif brush_type == 3:
    oled.fill_rect(70, 7, 52, 25, color=color)
  elif brush_type == 4:
    oled.circle(96, 19, 10, color=color)
  elif brush_type == 5:
    for r in range(1, 10):
      oled.circle(96, 19, r, color=color)
  elif brush_type == 6:
    for x in range(67, 125):
      for y in range(3, 35):
        oled.pixel(x, y, color=(255, 255, 255))

    oled.fill_rect(70, 7, 50, 25, color=0)

  oled.show()

#-------------------------------------------------------------------------------------------------------------------------------------

initialize_pin()

# 피에조 부저 PWM 초기화
buzzer = GPIO.PWM(BUZZER_PIN, 988)

# RGB LED PWM 초기화
GPIO.output(RGB_RED, GPIO.HIGH)
GPIO.output(RGB_GREEN, GPIO.HIGH)
GPIO.output(RGB_BLUE, GPIO.HIGH)

pwm_red = GPIO.PWM(RGB_RED, 50)
pwm_green = GPIO.PWM(RGB_GREEN, 50)
pwm_blue = GPIO.PWM(RGB_BLUE, 50)

pwm_red.start(0)
pwm_green.start(0)
pwm_blue.start(0)

set_rgb_led()

# 카메라 장치 열기
cap = VideoCapture(0)

# 키보드 이벤트 인식 객체
listener = keyboard.Listener(
  on_press = on_press
)

#oled 설정
color=(255, 255, 255)

oled.rect(1, 1, 128, 64, color=color)
oled.line(64, 1, 64, 64, color=color)
oled.line(64, 37, 128, 37, color=color)

for y, x in LOGO:
    for i in x:
        oled.pixel(i+1, y, color=color)

# 객체 생성
app = Flask(__name__)

# 홈 페이지
@app.route("/")
def index():
  return render_template("image_editor.html")

# 세로운 이미지 만들기
@app.route("/new_image")
# return -1: 오류 떴다, return 0: 사진 안찍었다, return "사진 이름"(.jpg 없이): 사진 찍었다
def new_image():
  global picture, picture_isTaken, background, frames, current_frame, image_name, cap

  # 카메라 안 열릴 때
  if not cap.isOpened():
    cv2.destroyAllWindows()
    print("camera failed to open")
    cap.release()
    return -1

  # 변수를 다시 초기화하기
  picture = None
  picture_isTaken = False
  background = None
  frames = [None] * frame_number
  current_frame = None
  image_name = None

  # 사진을 찍기
  ret = take_picture()

  # 사진을 못 찍었을 때
  if ret <= 0:
    cv2.destroyAllWindows()
    print("picture not taken")
    return ret

  ret = edit_image()

  # 사진을 못 찍었을 때
  if ret <= 0:
    cv2.destroyAllWindows()
    print("picture not taken")
    return ret

  ret = get_name()

  if ret <= 0:
    return ret

  # 이미지 에디터가 끝날 때 윈도우 삭제
  cv2.destroyAllWindows()

  # 이미지 파일 만들기
  cv2.imwrite("./static/images/" + image_name + ".jpg", frames[frame_number-1])

  # 이미지의 이름을 반환하기 (.jpg 없이)
  return image_name


if __name__ == "__main__":
  try:
    app.run(host="0.0.0.0")
  finally:
    red = 255
    green = 0
    blue = 0

    set_rgb_led()

    time.sleep(3)

    print("program exit")
    oled.fill(0)
    oled.show()
    pwm_red.stop()
    pwm_green.stop()
    pwm_blue.stop()
    cap.release()
    GPIO.cleanup()
