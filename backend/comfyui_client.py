"""
ComfyUI HTTP 클라이언트.
SDXL(DreamShaper XL) + IP-Adapter Plus 워크플로우를 ComfyUI API로 실행.
"""
import os
import time
import uuid
import shutil
from io import BytesIO

import requests

COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://comfyui-service:8188")
TIMEOUT_SEC = 300  # 최대 대기 5분
POLL_INTERVAL = 2

SDXL_CKPT      = "dreamshaper_xl.safetensors"
IPADAPTER_CKPT = "ip-adapter-plus_sdxl_vit-h.bin"
CLIP_VISION    = "clip_vit_h.safetensors"
NEGATIVE_PROMPT = "text, watermark, blurry, low quality, deformed, ugly, nsfw"


def _build_workflow(prompt: str, uploaded_image_name: str | None) -> dict:
    """ComfyUI API 워크플로우 JSON 구성."""
    seed = int(time.time() * 1000) % (2 ** 31)

    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": SDXL_CKPT},
        },
        "2": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["1", 1]},
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": NEGATIVE_PROMPT, "clip": ["1", 1]},
        },
        "4": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": None,  # 아래에서 채움
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "seed": seed,
                "steps": 30,
                "cfg": 7.5,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
            },
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]},
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {"images": ["7", 0], "filename_prefix": "ad_gen"},
        },
    }

    if uploaded_image_name:
        workflow["9"] = {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": IPADAPTER_CKPT},
        }
        workflow["10"] = {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": CLIP_VISION},
        }
        workflow["11"] = {
            "class_type": "LoadImage",
            "inputs": {"image": uploaded_image_name},
        }
        workflow["12"] = {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["1", 0],
                "ipadapter": ["9", 0],
                "image": ["11", 0],
                "clip_vision": ["10", 0],
                "weight": 0.5,
                "weight_type": "linear",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 1.0,
                "embeds_scaling": "V only",
            },
        }
        workflow["6"]["inputs"]["model"] = ["12", 0]
    else:
        workflow["6"]["inputs"]["model"] = ["1", 0]

    return workflow


def _upload_image(image_bytes: bytes) -> str:
    """ComfyUI에 이미지 업로드. 업로드된 파일명 반환."""
    name = f"product_{uuid.uuid4().hex[:8]}.png"
    resp = requests.post(
        f"{COMFYUI_URL}/upload/image",
        files={"image": (name, BytesIO(image_bytes), "image/png")},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["name"]


def _queue_prompt(workflow: dict) -> str:
    """워크플로우를 ComfyUI 큐에 등록. prompt_id 반환."""
    resp = requests.post(
        f"{COMFYUI_URL}/prompt",
        json={"prompt": workflow},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def _wait_for_result(prompt_id: str) -> tuple[str, str, str]:
    """완료까지 폴링. (filename, subfolder, type) 반환."""
    deadline = time.time() + TIMEOUT_SEC
    while time.time() < deadline:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
        resp.raise_for_status()
        history = resp.json()

        if prompt_id in history:
            entry = history[prompt_id]
            status = entry.get("status", {})

            if status.get("status_str") == "error":
                msgs = status.get("messages", [])
                raise RuntimeError(f"ComfyUI 추론 실패: {msgs}")

            for node_output in entry.get("outputs", {}).values():
                if "images" in node_output:
                    img = node_output["images"][0]
                    return img["filename"], img.get("subfolder", ""), img.get("type", "output")

        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"ComfyUI 응답 없음 ({TIMEOUT_SEC}s 초과): prompt_id={prompt_id}")


def _fetch_image(filename: str, subfolder: str, output_type: str) -> bytes:
    """생성된 이미지 바이트 다운로드."""
    resp = requests.get(
        f"{COMFYUI_URL}/view",
        params={"filename": filename, "subfolder": subfolder, "type": output_type},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content


def generate_image(prompt: str, product_image: bytes | None = None) -> bytes:
    """
    ComfyUI를 통해 SDXL 이미지 생성.
    product_image가 있으면 IP-Adapter Plus 적용.
    반환: PNG bytes
    """
    uploaded_name = None
    if product_image:
        uploaded_name = _upload_image(product_image)

    workflow = _build_workflow(prompt, uploaded_name)
    prompt_id = _queue_prompt(workflow)
    filename, subfolder, output_type = _wait_for_result(prompt_id)
    return _fetch_image(filename, subfolder, output_type)
