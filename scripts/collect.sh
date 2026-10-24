#!/usr/bin/env bash
# Запись матча с телефона и нарезка кадров. Использование: bash scripts/collect.sh match1
set -e
NAME=${1:-match}
mkdir -p videos frames
echo "Запись... Ctrl+C чтобы остановить"
scrcpy --no-audio --record=videos/$NAME.mp4 || true
ffmpeg -i videos/$NAME.mp4 -vf fps=1 frames/${NAME}_%04d.jpg
echo "Готово: frames/${NAME}_*.jpg"
