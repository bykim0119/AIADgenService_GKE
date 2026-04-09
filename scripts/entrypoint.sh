#!/bin/bash
set -e

echo "=== ComfyUI 모델 확인 ==="
python /workspace/download_models.py

echo "=== ComfyUI 서버 시작 (port 8188) ==="
exec python "${COMFYUI_PATH}/main.py" \
    --listen \
    --port 8188 \
    --disable-auto-launch
