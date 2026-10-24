"""ЭКСПЕРИМЕНТАЛЬНО: бот прямо на телефоне в Termux. Нужен ROOT.

Установка в Termux:
  pkg install python opencv-python tsu
  pip install onnxruntime numpy pyyaml   # если onnxruntime не ставится - см. docs/PHONE.md
Модель: models/best.onnx (экспорт из train.py).
Запуск: sudo python bot/run_termux.py
"""
import math
import subprocess
import time

import cv2
import numpy as np
import onnxruntime as ort
import yaml

from brain import decide

cfg = yaml.safe_load(open("bot/config.yaml"))
NAMES = ["me", "enemy", "ally", "bush", "wall", "gem"]  # порядок как в data.yaml!
sess = ort.InferenceSession("models/best.onnx")
INP = sess.get_inputs()[0].name
S = 640


def grab():
    raw = subprocess.run(["screencap", "-p"], capture_output=True).stdout
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)


def detect(img):
    h, w = img.shape[:2]
    x = cv2.resize(img, (S, S))[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255
    out = sess.run(None, {INP: x})[0][0].T  # (8400, 4+nc)
    scores = out[:, 4:]
    cls = scores.argmax(1)
    conf = scores.max(1)
    keep = conf > cfg["conf"]
    boxes, cls, conf = out[keep, :4], cls[keep], conf[keep]
    xyxy = np.stack([boxes[:, 0] - boxes[:, 2] / 2, boxes[:, 1] - boxes[:, 3] / 2,
                     boxes[:, 0] + boxes[:, 2] / 2, boxes[:, 1] + boxes[:, 3] / 2], 1)
    xyxy *= [w / S, h / S, w / S, h / S]
    idx = cv2.dnn.NMSBoxes(xyxy.tolist(), conf.tolist(), cfg["conf"], 0.5)
    return [(NAMES[cls[i]], float(conf[i]), xyxy[i].tolist()) for i in np.array(idx).flatten()]


def swipe(base, angle, ms):
    x, y = base
    r = cfg["joystick_radius"]
    tx, ty = int(x + r * math.cos(angle)), int(y + r * math.sin(angle))
    subprocess.Popen(["input", "swipe", str(x), str(y), str(tx), str(ty), str(ms)])


while True:
    img = grab()
    if img is None:
        continue
    act = decide(detect(img), cfg)
    if act["move"] is not None:
        swipe(cfg["move_joystick"], act["move"], 250)
    if act["attack"] is not None:
        swipe(cfg["attack_joystick"], act["attack"], 80)
    time.sleep(cfg["loop_delay"])
