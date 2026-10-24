# brawl-stars-ai

Исследовательский проект: YOLOv8 распознаёт объекты в Brawl Stars, простой бот играет по правилам.

> ⚠️ Боты нарушают ToS Supercell. Используйте **только отдельный аккаунт**, в учебных целях.

## Структура
```
scripts/collect.sh     запись матчей и нарезка кадров
train/train.py         обучение YOLO (Colab / Kaggle)
bot/config.yaml        координаты джойстиков, классы
bot/run_pc.py          бот: телефон по USB + ПК (рекомендуется)
bot/run_termux.py      бот прямо на телефоне (нужен root, экспериментально)
docs/PHONE.md          как запустить с телефона
```

## Шаги
1. **Данные:** `bash scripts/collect.sh match1` → кадры в `frames/`.
2. **Разметка:** Roboflow, классы `me, enemy, ally, bush, wall, gem`, экспорт YOLOv8.
3. **Обучение:** в Colab/Kaggle открыть ноутбук, `!git clone` репозиторий и
   `!python train/train.py --data путь/к/data.yaml`.
4. **Модель:** скачать `best.pt` в `models/`.
5. **Запуск:** см. [docs/PHONE.md](docs/PHONE.md).
