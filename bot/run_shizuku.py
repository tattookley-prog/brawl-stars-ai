"""Бот на планшете через Shizuku (rish). Без root и без ПК.

Нужно: Shizuku запущен, rish в $PREFIX/bin, termux-setup-storage выполнен,
models/best.onnx (экспорт opset=12).
Запуск: cd ~/brawl-stars-ai && python bot/run_shizuku.py
"""
import math
import subprocess
import time

import cv2
import numpy as np
import yaml

from brain import decide

cfg = yaml.safe_load(open("bot/config.yaml"))
NAMES = ["ally", "ball", "enemy", "me"]  # порядок как в data.yaml
net = cv2.dnn.readNetFromONNX("models/best.onnx")
S = 640
SHOT = "/sdcard/brawl_shot.png"

# одна постоянная rish-сессия: быстрее, чем запускать rish на каждую команду
sh = subprocess.Popen(["rish"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)


def run(cmd):
    sh.stdin.write(cmd + "; echo __OK__\n")
    sh.stdin.flush()
    while sh.stdout.readline().strip() != "__OK__":
        pass


def grab():
    run(f"screencap -p {SHOT}")
    return cv2.imread(SHOT)


def detect(img):
    h, w = img.shape[:2]
    net.setInput(cv2.dnn.blobFromImage(img, 1 / 255, (S, S), swapRB=True))
    out = net.forward()[0].T  # (8400, 4+nc)
    sc = out[:, 4:]
    cls = sc.argmax(1)
    conf = sc.max(1)
    k = conf > cfg["conf"]
    b, cls, conf = out[k, :4], cls[k], conf[k]
    if len(b) == 0:
        return []
    xywh = np.stack([(b[:, 0] - b[:, 2] / 2) * w / S, (b[:, 1] - b[:, 3] / 2) * h / S,
                     b[:, 2] * w / S, b[:, 3] * h / S], 1)
    idx = np.array(cv2.dnn.NMSBoxes(xywh.tolist(), conf.tolist(), cfg["conf"], 0.5)).flatten()
    return [(NAMES[cls[i]], float(conf[i]),
             (xywh[i, 0], xywh[i, 1], xywh[i, 0] + xywh[i, 2], xywh[i, 1] + xywh[i, 3])) for i in idx]


def swipe(base, angle, ms):
    x, y = base
    r = cfg["joystick_radius"]
    tx, ty = int(x + r * math.cos(angle)), int(y + r * math.sin(angle))
    sh.stdin.write(f"input swipe {x} {y} {tx} {ty} {ms} &\n")
    sh.stdin.flush()


print("Бот запущен. Ctrl+C - стоп.")
while True:
    t = time.time()
    img = grab()
    if img is None:
        continue
    dets = detect(img)
    act = decide(dets, cfg)
    if act["move"] is not None:
        swipe(cfg["move_joystick"], act["move"], 250)
    if act["attack"] is not None:
        swipe(cfg["attack_joystick"], act["attack"], 80)
    print(f"{[d[0] for d in dets]}  {1 / (time.time() - t):.1f} fps      ", end="\r")
    time.sleep(cfg["loop_delay"])
