"""Скачивает геймплей с YouTube и нарезает кадры для обучения детектора.

Установка: pip install yt-dlp opencv-python numpy
Использование:
    python scripts/youtube_frames.py --urls scripts/urls.txt --out frames/youtube
    python scripts/youtube_frames.py --urls scripts/urls.txt --every 2 --mask 0.78,0.0,1.0,0.3

urls.txt: одна ссылка на строку, строки с # игнорируются.
--mask x1,y1,x2,y2 (доли от ширины/высоты) закрашивает вебку чёрным. Можно указать несколько раз.

НЕ публикуйте полученные кадры: это чужие видео (только для личных исследований).
"""
import argparse
import subprocess
from pathlib import Path

import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--urls", required=True)
ap.add_argument("--out", default="frames/youtube")
ap.add_argument("--videos", default="videos/youtube")
ap.add_argument("--every", type=float, default=2.0, help="секунд между кадрами")
ap.add_argument("--diff", type=float, default=12.0, help="порог отличия кадров (0-255); меньше = больше похожих кадров")
ap.add_argument("--mask", action="append", default=[], help="x1,y1,x2,y2 в долях, закрасить область")
ap.add_argument("--max-height", type=int, default=1080)
ap.add_argument("--keep-video", action="store_true", help="не удалять видео после нарезки")
a = ap.parse_args()

out, vdir = Path(a.out), Path(a.videos)
out.mkdir(parents=True, exist_ok=True)
vdir.mkdir(parents=True, exist_ok=True)
masks = [tuple(map(float, m.split(","))) for m in a.mask]
urls = [u.strip() for u in open(a.urls, encoding="utf-8") if u.strip() and not u.startswith("#")]


def download(url):
    subprocess.run(["yt-dlp", "-f", f"bv*[height<={a.max_height}][ext=mp4]/bv*[height<={a.max_height}]",
                    "--no-playlist", "-o", str(vdir / "%(id)s.%(ext)s"), url], check=True)
    vid = subprocess.run(["yt-dlp", "--get-id", "--no-playlist", url],
                         capture_output=True, text=True).stdout.strip()
    files = list(vdir.glob(f"{vid}.*"))
    return vid, files[0] if files else None


def apply_masks(img):
    h, w = img.shape[:2]
    for x1, y1, x2, y2 in masks:
        img[int(y1 * h):int(y2 * h), int(x1 * w):int(x2 * w)] = 0
    return img


total = 0
for url in urls:
    print("==>", url)
    try:
        vid, path = download(url)
    except subprocess.CalledProcessError:
        print("   не удалось скачать, пропускаю")
        continue
    if path is None:
        continue
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = max(1, int(fps * a.every))
    prev, i, saved = None, 0, 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            ok, frame = cap.retrieve()
            if ok:
                frame = apply_masks(frame)
                small = cv2.cvtColor(cv2.resize(frame, (64, 36)), cv2.COLOR_BGR2GRAY).astype(np.float32)
                # пропускаем почти одинаковые кадры (меню, пауза, стояние на месте)
                if prev is None or np.abs(small - prev).mean() > a.diff:
                    cv2.imwrite(str(out / f"{vid}_{i:07d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                    prev, saved = small, saved + 1
        i += 1
    cap.release()
    if not a.keep_video:
        path.unlink(missing_ok=True)
    print(f"   сохранено {saved} кадров")
    total += saved
print(f"Готово: {total} кадров в {out}")
