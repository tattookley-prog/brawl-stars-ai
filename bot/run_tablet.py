"""Бот прямо на планшете Lenovo Legion Y700 (2025) БЕЗ root.

Termux подключается к самому планшету по беспроводной отладке (adb localhost),
поэтому screencap и input выполняются с правами shell.

Запуск (из корня репозитория):
    python bot/run_tablet.py --device localhost:ПОРТ
    python bot/run_tablet.py --device localhost:ПОРТ --debug   # только печать детекций, без нажатий
Подробно: docs/TABLET.md
"""
import argparse
import math
import subprocess
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort
import yaml

from brain import decide

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="bot/config_tablet.yaml")
ap.add_argument("--device", default=None)
ap.add_argument("--debug", action="store_true")
args = ap.parse_args()

cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
DEV = args.device or cfg.get("device") or ""
ADB = ["adb"] + (["-s", DEV] if DEV else [])
NAMES = cfg["names"]
S = cfg.get("imgsz", 640)

# --- проверка подключения ---
if DEV:
    subprocess.run(["adb", "connect", DEV], capture_output=True)
state = subprocess.run(ADB + ["get-state"], capture_output=True, text=True).stdout.strip()
if state != "device":
    sys.exit("adb не подключён. Выполните adb pair / adb connect (см. docs/TABLET.md)")

# --- модель ---
opts = ort.SessionOptions()
opts.intra_op_num_threads = 4
sess = ort.InferenceSession(cfg["model"], opts, providers=["CPUExecutionProvider"])
INP = sess.get_inputs()[0].name

# --- постоянная adb shell сессия для касаний (быстрее, чем новый процесс на каждое касание) ---
shell = subprocess.Popen(ADB + ["shell"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, text=True)


def grab():
    """Сырой скриншот (без PNG-сжатия - заметно быстрее на экране 3040x1904)."""
    raw = subprocess.run(ADB + ["exec-out", "screencap"], capture_output=True).stdout
    if len(raw) < 16:
        return None
    w, h = np.frombuffer(raw[:8], np.uint32)
    header = len(raw) - int(w) * int(h) * 4  # 12 или 16 байт в зависимости от версии Android
    if header < 12:
        return None
    img = np.frombuffer(raw[header:], np.uint8).reshape(int(h), int(w), 4)
    return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)


def detect(img):
    h, w = img.shape[:2]
    x = cv2.resize(img, (S, S))[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255
    out = sess.run(None, {INP: np.ascontiguousarray(x)})[0][0].T  # (N, 4+nc)
    scores = out[:, 4:]
    cls, conf = scores.argmax(1), scores.max(1)
    keep = conf > cfg["conf"]
    if not keep.any():
        return []
    b, cls, conf = out[keep, :4], cls[keep], conf[keep]
    xyxy = np.stack([b[:, 0] - b[:, 2] / 2, b[:, 1] - b[:, 3] / 2,
                     b[:, 0] + b[:, 2] / 2, b[:, 1] + b[:, 3] / 2], 1)
    xyxy *= [w / S, h / S, w / S, h / S]
    xywh = [[float(a), float(c), float(e - a), float(d - c)] for a, c, e, d in xyxy]
    idx = cv2.dnn.NMSBoxes(xywh, conf.tolist(), cfg["conf"], 0.5)
    return [(NAMES[cls[i]], float(conf[i]), xyxy[i].tolist()) for i in np.array(idx).flatten()]


def swipe(base, angle, ms):
    x, y = base
    r = cfg["joystick_radius"]
    tx, ty = int(x + r * math.cos(angle)), int(y + r * math.sin(angle))
    # '&' - чтобы движение и атака не ждали друг друга
    shell.stdin.write(f"input swipe {x} {y} {tx} {ty} {ms} &\n")
    shell.stdin.flush()


print(f"Бот запущен на {DEV or 'устройстве по умолчанию'}. Переключитесь в игру. Ctrl+C - стоп.")
try:
    while True:
        t0 = time.time()
        img = grab()
        if img is None:
            continue
        dets = detect(img)
        act = decide(dets, cfg)
        if args.debug:
            print(f"{1 / (time.time() - t0):.1f} FPS", [(d[0], round(d[1], 2)) for d in dets], act)
        else:
            if act["move"] is not None:
                swipe(cfg["move_joystick"], act["move"], 250)
            if act["attack"] is not None:
                swipe(cfg["attack_joystick"], act["attack"], 80)
        time.sleep(cfg["loop_delay"])
except KeyboardInterrupt:
    pass
finally:
    shell.terminate()
