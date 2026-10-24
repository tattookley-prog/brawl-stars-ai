# Lenovo Legion Y700 (2025): всё на планшете, без root

Termux подключается к самому планшету через беспроводную отладку ADB.
Обучение - в Colab/Kaggle (браузер на планшете), запуск бота - на планшете.

## 1. Режим разработчика
Настройки -> О планшете -> 7 раз нажать «Номер сборки».
Затем «Для разработчиков» -> включить **Отладка по Wi-Fi** (Wi-Fi должен быть включён).

## 2. Termux
Ставить из **F-Droid** (версия из Play Маркета устарела).
```bash
pkg update && pkg upgrade
pkg install android-tools git python python-numpy opencv-python
pip install pyyaml onnxruntime
termux-setup-storage      # доступ к Загрузкам (чтобы скопировать модель)
```
Если `onnxruntime` не ставится:
```bash
pkg install proot-distro && proot-distro install ubuntu && proot-distro login ubuntu
apt update && apt install -y python3-pip python3-opencv adb git
pip install onnxruntime numpy pyyaml --break-system-packages
```

## 3. Сопряжение планшета с самим собой
1. Откройте разделённый экран: Termux + Настройки -> Отладка по Wi-Fi.
2. Нажмите «Подключить устройство с помощью кода».
```bash
adb pair localhost:ПОРТ_ИЗ_ОКНА_С_КОДОМ     # ввести 6-значный код
adb connect localhost:ПОРТ_С_ЭКРАНА_ОТЛАДКИ  # это ДРУГОЙ порт!
adb devices                                  # должно быть: localhost:XXXXX  device
```
Сопряжение делается один раз. После перезагрузки или выключения Wi-Fi - только `adb connect` с новым портом.

## 4. Не дать системе убить Termux
- Настройки -> Приложения -> Termux -> Батарея -> **Без ограничений**.
- В Termux: `termux-wake-lock`.
- В Legion Space/игровом режиме не добавляйте ограничения фоновых процессов.

## 5. Проект и модель
```bash
git clone https://github.com/tattookley-prog/brawl-stars-ai
cd brawl-stars-ai && mkdir -p models
cp ~/storage/downloads/best.onnx models/
```
(репозиторий приватный - для clone нужен токен: GitHub -> Settings -> Developer settings -> Personal access tokens, вводится вместо пароля.)

## 6. Координаты джойстиков
Экран Y700 (2025) - 3040x1904. В `bot/config_tablet.yaml` стоят примерные значения.
Включите «Для разработчиков» -> **Местоположение указателя**, зайдите в тренировку,
коснитесь центров левого и правого джойстика, запишите X/Y в конфиг.

## 7. Запуск
```bash
# сначала проверка: только печатает, что видит модель, и FPS
python bot/run_tablet.py --device localhost:ПОРТ --debug
# боевой режим
python bot/run_tablet.py --device localhost:ПОРТ
```
После запуска переключитесь в Brawl Stars. Остановить - вернуться в Termux, Ctrl+C
(клавиша CTRL есть в доп. ряду клавиатуры Termux).

## Ожидаемая производительность
- Скриншот 3040x1904 через adb - основное узкое место, ~4-8 кадров/с.
- YOLOv8n 640 на Snapdragon 8 Gen 3 (CPU) - ~30-60 мс.
- Ускорить: понизить разрешение игры не получится, но можно обучить модель на `imgsz=480`;
  следующий шаг - своё приложение с MediaProjection (30+ кадров/с).

## Частые проблемы
| Проблема | Решение |
|---|---|
| `adb не подключён` | Повторить `adb connect localhost:НОВЫЙ_ПОРТ` |
| Нажимает не туда | Проверить координаты и что игра в альбомной ориентации |
| Ничего не находит | Проверить порядок `names` = порядок в data.yaml, снизить `conf` |
| Termux закрывается | Батарея -> Без ограничений, `termux-wake-lock` |
| Сильно греется | Включить вентилятор/режим производительности в Legion Space |
