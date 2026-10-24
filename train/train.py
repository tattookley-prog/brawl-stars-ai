"""Обучение YOLOv8. Работает в Colab, Kaggle и локально.

Colab:  !python train/train.py --data /content/brawl-stars-1/data.yaml --out /content/drive/MyDrive/brawl_yolo
Kaggle: !python train/train.py --data /kaggle/input/brawl-stars/data.yaml --out /kaggle/working/runs --device 0,1
"""
import argparse
from ultralytics import YOLO

p = argparse.ArgumentParser()
p.add_argument("--data", required=True)
p.add_argument("--model", default="yolov8n.pt")
p.add_argument("--epochs", type=int, default=100)
p.add_argument("--imgsz", type=int, default=640)
p.add_argument("--batch", type=int, default=16)
p.add_argument("--device", default="0")
p.add_argument("--out", default="runs")
p.add_argument("--resume", help="путь к last.pt для продолжения")
a = p.parse_args()

if a.resume:
    YOLO(a.resume).train(resume=True)
else:
    dev = [int(x) for x in a.device.split(",")] if "," in a.device else a.device
    model = YOLO(a.model)
    model.train(data=a.data, epochs=a.epochs, imgsz=a.imgsz, batch=a.batch,
                device=dev, project=a.out)
    best = f"{model.trainer.save_dir}/weights/best.pt"
    m = YOLO(best)
    m.export(format="onnx")
    m.export(format="tflite")
    print("Готово:", best)
