# Запуск с телефона

## Вариант A (рекомендуется): телефон + любой ПК/ноутбук
1. На телефоне: Настройки → О телефоне → 7 раз нажать «Номер сборки» → Для разработчиков → **Отладка по USB** (+ на Xiaomi «Отладка по USB (настройки безопасности)»).
2. На ПК: установить [platform-tools (adb)](https://developer.android.com/tools/releases/platform-tools), Python 3.10+, `pip install -r requirements.txt`.
3. Подключить кабелем, `adb devices` → разрешить на телефоне.
4. Положить `best.pt` в `models/`, поправить координаты в `bot/config.yaml`.
5. Открыть матч и запустить `python bot/run_pc.py`.

Без кабеля: `adb tcpip 5555`, затем `adb connect IP_телефона:5555`.

## Вариант B: только телефон, с root
1. Установить Termux (из F-Droid, не из Play Market).
2. `pkg install git python opencv-python tsu` и `git clone` репозитория.
3. `pip install onnxruntime numpy pyyaml`. Если onnxruntime не собирается, используйте `proot-distro install ubuntu` и ставьте внутри Ubuntu.
4. Скопировать `best.onnx` в `models/`, запустить `sudo python bot/run_termux.py`.
5. Переключиться в игру — скрипт работает в фоне.

## Вариант C: только телефон, без root
Нужно Android-приложение на Kotlin: MediaProjection (экран) + AccessibilityService (`dispatchGesture`) + TFLite (`best.tflite`). Шаблона пока нет — это следующий этап.

## iPhone
Без джейлбрейка — никак. Только вариант A не подходит тоже (adb нет).
