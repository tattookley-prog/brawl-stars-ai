"""Записывает ваш геймплей на планшете: кадры + положение джойстиков (для behavioral cloning).

Запуск в Termux (adb уже подключён, см. docs/TABLET.md):
    python scripts/record_touches.py --device localhost:ПОРТ --out data/session1
Зате�� переключитесь в игру и играйте. Остановка: вернуться в Termux, Ctrl+C.

Результат:
    data/session1/frames/000123.jpg   кадры
    data/session1/actions.jsonl       {"frame":..., "t":..., "move":[dx,dy]|null, "attack":[dx,dy]|null, "fire":bool}
    dx,dy в диапазоне -1..1 (отклонение пальца от центра джойстика / joystick_radius).

Джойстики определяются по config_tablet.yaml: касание в левой половине экрана = движение,
в правой = атака. "fire" = палец отпущен с правой половины (выстрел/автоатака по тапу).
"""
import argparse
import json
import re
import subprocess
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

ap = argparse.ArgumentParser()
ap.add_argument("--config", default="bot/config_tablet.yaml")
ap.add_argument("--device", default=None)
ap.add_argument("--out", default="data/session")
ap.add_argument("--scale", type=float, default=0.5, help="уменьшение кадров при сохранении")
ap.add_argument("--rotate", type=int, default=-1, choices=[-1, 0, 1, 2, 3],
                help="поворот сенсора относительно экрана; -1 = определить автоматически")
a = ap.parse_args()

cfg = yaml.safe_load(open(a.config, encoding="utf-8"))
DEV = a.device or cfg.get("device") or ""
ADB = ["adb"] + (["-s", DEV] if DEV else [])
out = Path(a.out)
(out / "frames").mkdir(parents=True, exist_ok=True)


def sh(cmd):
    return subprocess.run(ADB + ["shell", cmd], capture_output=True, text=True).stdout


# --- размеры экрана и сенсора ---
m = re.search(r"(\d+)x(\d+)", sh("wm size").splitlines()[-1])
NAT_W, NAT_H = int(m.group(1)), int(m.group(2))  # натуральная ориентация

info = sh("getevent -lp")
touch_dev, max_x, max_y = None, None, None
for block in re.split(r"\nadd device \d+: ", "\n" + info):
    if "ABS_MT_POSITION_X" in block:
        touch_dev = block.split()[0]
        max_x = int(re.search(r"ABS_MT_POSITION_X.*?max (\d+)", block).group(1))
        max_y = int(re.search(r"ABS_MT_POSITION_Y.*?max (\d+)", block).group(1))
        break
if touch_dev is None:
    raise SystemExit("Сенсорный экран н�� найден в getevent -lp")
print(f"Сенсор: {touch_dev}, диапазон {max_x}x{max_y}, экран {NAT_W}x{NAT_H}")


def rotation():
    if a.rotate >= 0:
        return a.rotate
    r = re.search(r"mCurrentRotation=(?:ROTATION_)?(\d+)", sh("dumpsys window displays")) or \
        re.search(r"SurfaceOrientation:\s*(\d)", sh("dumpsys input"))
    v = int(r.group(1)) if r else 0
    return {0: 0, 90: 1, 180: 2, 270: 3}.get(v, v)


ROT = rotation()
print("Поворот экрана:", ROT, "(если касания пишутся неверно, попробуйте --rotate 0..3)")


def to_screen(rx, ry):
    """Сырые координаты сенсора -> пиксели текущей (альбомной) ориентации."""
    x, y = rx / max_x * NAT_W, ry / max_y * NAT_H
    if ROT == 0:
        return x, y
    if ROT == 1:
        return y, NAT_W - x
    if ROT == 2:
        return NAT_W - x, NAT_H - y
    return NAT_H - y, x


# --- поток чтения касаний ---
slots = {}           # slot -> {"x":..,"y":..} активные пальцы
cur_slot = 0
fire_flag = False
lock = threading.Lock()
SCREEN_W = max(NAT_W, NAT_H)


def read_touches():
    global cur_slot, fire_flag
    p = subprocess.Popen(ADB + ["shell", f"getevent -l {touch_dev}"], stdout=subprocess.PIPE, text=True)
    for line in p.stdout:
        parts = line.split()
        if len(parts) < 3:
            continue
        code, val = parts[-2], parts[-1]
        try:
            v = int(val, 16)
        except ValueError:
            continue
        with lock:
            if code == "ABS_MT_SLOT":
                cur_slot = v
            elif code == "ABS_MT_TRACKING_ID":
                if val == "ffffffff":
                    s = slots.pop(cur_slot, None)
                    if s and "x" in s and to_screen(s["x"], s["y"])[0] > SCREEN_W / 2:
                        fire_flag = True
                else:
                    slots[cur_slot] = {}
            elif code == "ABS_MT_POSITION_X":
                slots.setdefault(cur_slot, {})["x"] = v
            elif code == "ABS_MT_POSITION_Y":
                slots.setdefault(cur_slot, {})["y"] = v


threading.Thread(target=read_touches, daemon=True).start()


def joystick_vec(px, py, base):
    r = cfg["joystick_radius"]
    dx, dy = (px - base[0]) / r, (py - base[1]) / r
    n = max(1.0, (dx * dx + dy * dy) ** 0.5)
    return [round(dx / n, 3), round(dy / n, 3)]


def current_action():
    global fire_flag
    move = attack = None
    with lock:
        for s in slots.values():
            if "x" not in s or "y" not in s:
                continue
            px, py = to_screen(s["x"], s["y"])
            if px < SCREEN_W / 2:
                move = joystick_vec(px, py, cfg["move_joystick"])
            else:
                attack = joystick_vec(px, py, cfg["attack_joystick"])
        fire, fire_flag = fire_flag, False
    return move, attack, fire


def grab():
    raw = subprocess.run(ADB + ["exec-out", "screencap"], capture_output=True).stdout
    if len(raw) < 16:
        return None
    w, h = (int(v) for v in np.frombuffer(raw[:8], np.uint32))
    header = len(raw) - w * h * 4
    if header < 12:
        return None
    img = np.frombuffer(raw[header:], np.uint8).reshape(h, w, 4)
    return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)


print("Запись идёт. Переключитесь в игру. Ctrl+C в Termux - стоп.")
n, t0 = 0, time.time()
with open(out / "actions.jsonl", "a", encoding="utf-8") as f:
    try:
        while True:
            img = grab()
            if img is None:
                continue
            move, attack, fire = current_action()
            if a.scale != 1:
                img = cv2.resize(img, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_AREA)
            name = f"{n:06d}.jpg"
            cv2.imwrite(str(out / "frames" / name), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            f.write(json.dumps({"frame": name, "t": round(time.time() - t0, 3),
                                "move": move, "attack": attack, "fire": fire}) + "\n")
            n += 1
            if n % 50 == 0:
                f.flush()
                print(f"{n} кадров, {n / (time.time() - t0):.1f} к/с")
    except KeyboardInterrupt:
        pass
print(f"Сохранено {n} кадров в {out}")
