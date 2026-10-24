"""Бот: телефон подключён к ПК по USB (включена отладка по USB).

Запуск: python bot/run_pc.py
Экран берётся через `adb exec-out screencap` (просто, но ~3-5 кадров/с).
Для скорости позже можно перейти на scrcpy + захват окна.
"""
import math
import subprocess
import time

import cv2
import numpy as np
import yaml
from ultralytics import YOLO

from brain import decide

cfg = yaml.safe_load(open("bot/config.yaml"))
model = YOLO(cfg["model"])


def grab():
    raw = subprocess.run(["adb", "exec-out", "screencap", "-p"], capture_output=True).stdout
    return cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)


def swipe(base, angle, ms=120):
    x, y = base
    r = cfg["joystick_radius"]
    tx, ty = int(x + r * math.cos(angle)), int(y + r * math.sin(angle))
    subprocess.Popen(["adb", "shell", "input", "swipe", str(x), str(y), str(tx), str(ty), str(ms)])


print("Бот запущен. Ctrl+C - стоп.")
while True:
    frame = grab()
    if frame is None:
        continue
    r = model(frame, conf=cfg["conf"], verbose=False)[0]
    dets = [(r.names[int(b.cls)], float(b.conf), b.xyxy[0].tolist()) for b in r.boxes]
    act = decide(dets, cfg)
    if act["move"] is not None:
        swipe(cfg["move_joystick"], act["move"], 250)
    if act["attack"] is not None:
        swipe(cfg["attack_joystick"], act["attack"], 80)
    time.sleep(cfg["loop_delay"])
