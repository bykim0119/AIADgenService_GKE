"""
SDXL + IP-Adapter-plus + PIL 합성 버전 (DreamShaper XL / RealVisXL 등 호환)

현재 역할: build_sd_prompt / write_copy / overlay_copy_on_image 제공.
이미지 생성(generate_image)은 ComfyUI API(comfyui_client.py)로 이전.
torch/diffusers는 _load_ip_pipeline 내부에서만 임포트 (Worker에 torch 불필요).
"""
import io
import os
import threading
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv
from categories import CATEGORIES
from themes import THEMES

load_dotenv()

_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

HF_TOKEN = os.getenv("HF_TOKEN")
SDXL_MODEL = "Lykon/dreamshaper-xl-1-0"
IP_ADAPTER_REPO = "h94/IP-Adapter"
IP_ADAPTER_SUBFOLDER = "sdxl_models"
IP_ADAPTER_WEIGHT = "ip-adapter-plus_sdxl_vit-h.bin"
IP_CLIP_ENCODER_SUBFOLDER = "models/image_encoder"

_ip_pipe = None
_ip_pipe_lock = threading.Lock()
_rembg_session = None


def is_model_ready() -> bool:
    return _ip_pipe is not None


def _get_rembg_session():
    global _rembg_session
    if _rembg_session is None:
        from rembg import new_session
        _rembg_session = new_session(providers=["CPUExecutionProvider"])
    return _rembg_session


def _load_ip_pipeline():
    """SDXL + h94/IP-Adapter-plus(ViT-H, patch-level) 로컬 파이프라인 초기화.
    ComfyUI 도입 이후 직접 호출되지 않음. 로컬 디버깅용으로 보존.
    """
    import torch
    from diffusers import StableDiffusionXLPipeline
    from transformers import CLIPVisionModelWithProjection

    global _ip_pipe
    if _ip_pipe is not None:
        return

    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    DTYPE = torch.float16 if torch.cuda.is_available() else torch.float32

    with _ip_pipe_lock:
        if _ip_pipe is not None:
            return

        image_encoder = CLIPVisionModelWithProjection.from_pretrained(
            IP_ADAPTER_REPO,
            subfolder=IP_CLIP_ENCODER_SUBFOLDER,
            torch_dtype=DTYPE,
        )

        _ip_pipe = StableDiffusionXLPipeline.from_pretrained(
            SDXL_MODEL,
            torch_dtype=DTYPE,
            token=HF_TOKEN,
            image_encoder=image_encoder,
        )
        _ip_pipe.load_ip_adapter(
            IP_ADAPTER_REPO,
            subfolder=IP_ADAPTER_SUBFOLDER,
            weight_name=IP_ADAPTER_WEIGHT,
        )
        _ip_pipe.set_ip_adapter_scale(0.2)

        _ip_pipe.to(DEVICE)


def build_sd_prompt(user_input: str, category: str, theme: str) -> str:
    """GPT-5-mini를 사용해 카테고리/테마/사용자 입력을 기반으로 SDXL용 영문 프롬프트 생성."""
    category_prompt = CATEGORIES[category]["prompt"]
    theme_prompt = THEMES[theme]["prompt"]

    response = _openai.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert at writing Stable Diffusion XL image generation prompts for advertisement images. "
                    "CRITICAL RULES:\n"
                    "1. Output MUST be entirely in English — no Korean, no other languages, English only.\n"
                    "2. The prompt is fed to a CLIP encoder with a hard 77-token limit. Keep it strictly under 55 English words.\n"
                    "3. Structure: [subject/person/action/food] [mood/lighting] [style keywords]. Most important content first.\n"
                    "4. If the user mentions a person, action, or specific food, it MUST appear at the start of the prompt.\n"
                    "5. Style and atmosphere keywords go last — they are expendable if truncated.\n"
                    "6. Output only the prompt text. No explanation, no Korean, no other commentary."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User scene description (highest priority): {user_input}\n"
                    f"Category context (atmosphere reference): {category_prompt}\n"
                    f"Visual theme (style reference): {theme_prompt}\n\n"
                    "Write the SDXL prompt:"
                ),
            },
        ],
    )
    return response.choices[0].message.content.strip()


def _composite_product(base_img: Image.Image, product_img: Image.Image, position: str = "bottom-center") -> Image.Image:
    """배경 제거 + 소프트 엣지 + 그림자 + '제품이미지' 라벨로 자연스럽게 합성."""
    from rembg import remove
    from PIL import ImageFilter, ImageDraw, ImageFont

    base_w, base_h = base_img.size
    product_size = int(base_w * 0.30)
    shadow_blur = int(product_size * 0.06)
    shadow_offset_x = int(product_size * 0.03)
    shadow_offset_y = int(product_size * 0.05)

    product_no_bg = remove(product_img, session=_get_rembg_session()).resize((product_size, product_size), Image.LANCZOS)

    r, g, b, a = product_no_bg.split()
    a_soft = a.filter(ImageFilter.GaussianBlur(2))
    product_no_bg = Image.merge("RGBA", (r, g, b, a_soft))

    shadow_alpha = a_soft.point(lambda x: int(x * 0.45))
    shadow_layer = Image.new("RGBA", (product_size, product_size), (0, 0, 0, 0))
    shadow_layer.putalpha(shadow_alpha)
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur))

    canvas_w = product_size + shadow_offset_x + shadow_blur
    canvas_h = product_size + shadow_offset_y + shadow_blur
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    canvas.paste(shadow_layer, (shadow_offset_x, shadow_offset_y), shadow_layer)
    canvas.paste(product_no_bg, (0, 0), product_no_bg)

    margin = int(base_w * 0.03)
    positions = {
        "bottom-center": ((base_w - canvas_w) // 2,   base_h - canvas_h - margin),
        "bottom-left":   (margin,                      base_h - canvas_h - margin),
        "bottom-right":  (base_w - canvas_w - margin,  base_h - canvas_h - margin),
        "center-left":   (margin,                      (base_h - canvas_h) // 2),
        "center-right":  (base_w - canvas_w - margin,  (base_h - canvas_h) // 2),
    }
    x, y = positions.get(position, positions["bottom-center"])

    result = base_img.convert("RGBA")
    result.paste(canvas, (x, y), canvas)

    label_font_size = int(base_w * 0.022)
    label_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    try:
        label_font = ImageFont.truetype(label_path, label_font_size)
    except OSError:
        label_font = ImageFont.load_default()

    draw = ImageDraw.Draw(result)
    label = "제품이미지"
    bbox = draw.textbbox((0, 0), label, font=label_font)
    lw = bbox[2] - bbox[0]
    lh = bbox[3] - bbox[1]
    pad = int(label_font_size * 0.4)
    lx = x + (canvas_w - lw - pad * 2) // 2
    ly = y - lh - pad * 2 - int(base_h * 0.005)

    draw.rounded_rectangle(
        [lx, ly, lx + lw + pad * 2, ly + lh + pad * 2],
        radius=int(label_font_size * 0.3),
        fill=(0, 0, 0, 160),
    )
    draw.text((lx + pad, ly + pad), label, font=label_font, fill=(255, 255, 255, 230))

    return result.convert("RGB")


def generate_image(prompt: str, product_image: bytes = None, position: str = "bottom-center") -> bytes:
    """
    product_image 있을 때: SDXL + IP-Adapter-plus로 스타일 반영 후 PIL 합성
    product_image 없을 때: SDXL 텍스트 생성
    """
    _load_ip_pipeline()

    negative_prompt = "text, watermark, blurry, low quality, deformed, ugly"
    dummy_img = Image.new("RGB", (224, 224), (128, 128, 128))

    if product_image:
        # IP-Adapter로 원본 이미지를 생성에 자연스럽게 반영 (PIL 합성 없음)
        ref_img = Image.open(io.BytesIO(product_image)).convert("RGB")
        _ip_pipe.set_ip_adapter_scale(0.5)
        result = _ip_pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            ip_adapter_image=ref_img,
            num_inference_steps=30,
            guidance_scale=7.5,
            height=1024,
            width=1024,
        ).images[0]
    else:
        _ip_pipe.set_ip_adapter_scale(0.0)
        result = _ip_pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            ip_adapter_image=dummy_img,
            num_inference_steps=30,
            guidance_scale=7.5,
            height=1024,
            width=1024,
        ).images[0]

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()


def write_copy(user_input: str, category: str, history: list) -> dict:
    """GPT-5-mini를 사용해 멀티턴 컨텍스트를 반영한 한국어 광고 문구 생성.
    반환: {"copy": str, "message": str}
    """
    import json as _json
    category_label = CATEGORIES[category]["label"]

    messages = [
        {
            "role": "system",
            "content": (
                f"당신은 {category_label} 업종 소상공인을 위한 광고 카피라이터입니다. "
                "반드시 아래 JSON 형식으로만 응답하세요:\n"
                '{"copy": "광고 문구", "message": "사용자에게 전달할 안내"}\n\n'
                "규칙:\n"
                "- copy: 임팩트 있는 한국어 광고 문구, 반드시 2줄 이내(줄바꿈 \\n 사용), 정보가 부족해도 반드시 작성\n"
                "- message: 추가 정보 요청이나 피드백 제안 등 사용자에게 하고 싶은 말. 없으면 빈 문자열\n"
                "- 이전 대화 히스토리가 있다면 피드백을 반영해 copy를 개선\n"
                "- copy 외 설명·안내는 반드시 message에만 작성"
            ),
        }
    ]

    for turn in history:
        messages.append({"role": "user", "content": turn["user_input"]})
        messages.append({"role": "assistant", "content": f'{{"copy": {_json.dumps(turn["copy"], ensure_ascii=False)}, "message": ""}}'})

    messages.append({"role": "user", "content": user_input})

    response = _openai.chat.completions.create(
        model="gpt-5-mini",
        messages=messages,
    )
    content = response.choices[0].message.content.strip()
    try:
        # 코드블록 래핑 제거 후 JSON 파싱
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        data = _json.loads(content)
    except _json.JSONDecodeError:
        data = {"copy": content, "message": ""}
    return {
        "copy": data.get("copy", content).strip(),
        "message": data.get("message", "").strip(),
    }


FONT_MAP = {
    "nanumpen":              "/usr/share/fonts/truetype/nanum/NanumPen.ttf",
    "nanumgothicbold":       "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "nanumgothicextrabold":  "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
    "nanummyeongjobold":     "/usr/share/fonts/truetype/nanum/NanumMyeongjoBold.ttf",
    "nanumbarun":            "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
}


def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple:
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (r, g, b, alpha)


def _auto_outline(text_rgba: tuple) -> tuple:
    r, g, b, _ = text_rgba
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return (20, 20, 20, 200) if luminance > 128 else (240, 240, 240, 200)


def overlay_copy_on_image(
    image_bytes: bytes,
    copy_text: str,
    text_position: str = "top",
    font_name: str = "nanumpen",
    text_color_hex: str = "#FFF5B4",
    font_size_ratio: float = 0.052,
) -> bytes:
    """커스터마이징 가능한 폰트/색상/크기로 카피 문구 오버레이."""
    from PIL import ImageDraw, ImageFont

    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    gradient_h = int(h * 0.30)

    if text_position == "top":
        for y in range(gradient_h):
            alpha = int(165 * (1 - y / gradient_h) ** 1.5)
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    elif text_position == "bottom":
        for y in range(gradient_h):
            alpha = int(165 * (1 - y / gradient_h) ** 1.5)
            draw.line([(0, h - 1 - y), (w, h - 1 - y)], fill=(0, 0, 0, alpha))
    else:
        bar_h = int(h * 0.22)
        bar_y = (h - bar_h) // 2
        for y in range(bar_h):
            ratio = 1 - abs(y - bar_h / 2) / (bar_h / 2)
            alpha = int(150 * ratio)
            draw.line([(0, bar_y + y), (w, bar_y + y)], fill=(0, 0, 0, alpha))

    font_size = int(w * max(0.02, min(0.12, font_size_ratio)))
    font_path = FONT_MAP.get(font_name, FONT_MAP["nanumpen"])
    try:
        font = ImageFont.truetype(font_path, font_size)
    except OSError:
        font = ImageFont.truetype(FONT_MAP["nanumgothicbold"], font_size)

    text_color = _hex_to_rgba(text_color_hex, 255)
    outline_color = _auto_outline(text_color)
    tilts = [-2.5, 1.5, -1.0] if font_name == "nanumpen" else [0, 0, 0]

    lines = [l.strip() for l in copy_text.strip().split("\n") if l.strip()]
    line_h = int(font_size * 1.5)
    total_text_h = line_h * len(lines)

    if text_position == "top":
        y_base = (gradient_h - total_text_h) // 2
    elif text_position == "bottom":
        y_base = h - gradient_h + (gradient_h - total_text_h) // 2
    else:
        y_base = (h - total_text_h) // 2

    for i, line in enumerate(lines):
        tilt = tilts[i % len(tilts)]

        tmp = Image.new("RGBA", (w, line_h * 2), (0, 0, 0, 0))
        tmp_draw = ImageDraw.Draw(tmp)
        bbox = tmp_draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        tx = (w - text_w) // 2
        ty = line_h // 4

        for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
            tmp_draw.text((tx + dx, ty + dy), line, font=font, fill=outline_color)
        tmp_draw.text((tx, ty), line, font=font, fill=text_color)

        if tilt != 0:
            tmp = tmp.rotate(tilt, resample=Image.BICUBIC, expand=False)

        y_cur = y_base + i * line_h
        overlay.paste(tmp, (0, y_cur - line_h // 4), tmp)

    result = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()
