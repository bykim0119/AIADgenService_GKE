#!/usr/bin/env python3
"""
ComfyUI 모델 최초 다운로드 스크립트.
PVC 마운트 후 컨테이너 시작 시 실행 — 이미 존재하는 파일은 스킵.
"""
import os
import shutil
from pathlib import Path
from huggingface_hub import hf_hub_download

COMFYUI_PATH = os.environ.get("COMFYUI_PATH", "/workspace/ComfyUI")
MODELS_DIR = Path(COMFYUI_PATH) / "models"
HF_TOKEN = os.environ.get("HF_TOKEN")

CHECKPOINTS_DIR = MODELS_DIR / "checkpoints"
IPADAPTER_DIR   = MODELS_DIR / "ipadapter"
CLIP_VISION_DIR = MODELS_DIR / "clip_vision"

for d in [CHECKPOINTS_DIR, IPADAPTER_DIR, CLIP_VISION_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def download(dest: Path, repo_id: str, filename: str) -> None:
    if dest.exists():
        print(f"  [SKIP] {dest.name}")
        return
    print(f"  [GET]  {repo_id}/{filename}")
    src = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        token=HF_TOKEN,
        cache_dir="/tmp/hf_cache",
    )
    shutil.copy2(src, dest)
    print(f"  [OK]   {dest}")


# SDXL 체크포인트 (DreamShaper XL — CivitAI 원본 단일 파일)
# Version ID: civitai.com/models/112902 → 다운로드 URL에서 확인
# TODO: GKE 배포 전 CIVITAI_VERSION_ID 실제 값 확인 필요
print("▶ SDXL 체크포인트 (DreamShaper XL — CivitAI)")
CIVITAI_TOKEN = os.environ.get("CIVITAI_API_KEY", "")
CIVITAI_VERSION_ID = "126688"  # alpha2 (xl1.0) — HF Lykon/dreamshaper-xl-1-0 과 동일 모델
CKPT_DEST = CHECKPOINTS_DIR / "dreamshaper_xl.safetensors"

if not CKPT_DEST.exists():
    if not CIVITAI_TOKEN:
        print("  [ERROR] CIVITAI_API_KEY 환경변수 없음 — k8s secret에 추가 필요")
    else:
        import requests
        url = f"https://civitai.com/api/download/models/{CIVITAI_VERSION_ID}"
        print(f"  [GET] {url}")
        # requests가 리다이렉트를 처리하며, CDN URL에는 Authorization 헤더를 보내지 않음
        with requests.get(url, headers={"Authorization": f"Bearer {CIVITAI_TOKEN}"},
                          stream=True, timeout=3600) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(CKPT_DEST, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        print(f"  {downloaded/1e9:.2f}/{total/1e9:.2f} GB", end="\r")
        print(f"\n  [OK] {CKPT_DEST}")
else:
    print(f"  [SKIP] {CKPT_DEST.name}")

# IP-Adapter Plus SDXL
print("▶ IP-Adapter Plus SDXL (ViT-H)")
download(
    IPADAPTER_DIR / "ip-adapter-plus_sdxl_vit-h.bin",
    repo_id="h94/IP-Adapter",
    filename="sdxl_models/ip-adapter-plus_sdxl_vit-h.bin",
)

# CLIP Vision ViT-H (IP-Adapter 이미지 인코더)
print("▶ CLIP Vision ViT-H")
download(
    CLIP_VISION_DIR / "clip_vit_h.safetensors",
    repo_id="h94/IP-Adapter",
    filename="models/image_encoder/model.safetensors",
)

print("✓ 모든 모델 준비 완료")
