import io
import os
import threading
import torch
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv
from categories import CATEGORIES
from themes import THEMES

load_dotenv()

_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

HF_TOKEN = os.getenv("HF_TOKEN")
# FLUX.1-schnell NF4 - Apache 2.0
FLUX_MODEL = "black-forest-labs/FLUX.1-schnell"

_flux_pipe = None
_flux_lock = threading.Lock()
_rembg_session = None


def is_model_ready() -> bool:
    return _flux_pipe is not None


def _get_rembg_session():
    global _rembg_session
    if _rembg_session is None:
        from rembg import new_session
        _rembg_session = new_session(providers=["CPUExecutionProvider"])
    return _rembg_session


def _load_flux_pipeline():
    """FLUX.1-schnell + NF4 4-bit 양자화 파이프라인 초기화."""
    global _flux_pipe
    if _flux_pipe is not None:
        return
    with _flux_lock:
        if _flux_pipe is not None:  # 락 획득 사이 다른 스레드가 먼저 로드한 경우
            return

        from diffusers import FluxPipeline, FluxTransformer2DModel
        from transformers import BitsAndBytesConfig

        nf4_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        from transformers import T5EncoderModel

        transformer = FluxTransformer2DModel.from_pretrained(
            FLUX_MODEL,
            subfolder="transformer",
            quantization_config=nf4_config,
            torch_dtype=torch.bfloat16,
            token=HF_TOKEN,
        )

        text_encoder_2 = T5EncoderModel.from_pretrained(
            FLUX_MODEL,
            subfolder="text_encoder_2",
            quantization_config=nf4_config,
            torch_dtype=torch.bfloat16,
            token=HF_TOKEN,
        )

        _flux_pipe = FluxPipeline.from_pretrained(
            FLUX_MODEL,
            transformer=transformer,
            text_encoder_2=text_encoder_2,
            torch_dtype=torch.bfloat16,
            token=HF_TOKEN,
        )
        _flux_pipe.to("cuda")


def build_sd_prompt(user_input: str, category: str, theme: str) -> str:
    """GPT-5-mini를 사용해 카테고리/테마/사용자 입력을 기반으로 FLUX용 영문 프롬프트 생성."""
    category_prompt = CATEGORIES[category]["prompt"]
    theme_prompt = THEMES[theme]["prompt"]

    response = _openai.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert at writing FLUX image generation prompts for advertisement images. "
                    "Given a business category context, visual theme, and user description, "
                    "write a concise, vivid English prompt suitable for FLUX. "
                    "Output only the prompt text, no explanation. "
                    "IMPORTANT: Keep the prompt strictly under 60 words. "
                    "Do NOT include any instructions about placing, showing, or inserting a product image — that is handled separately."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Category context: {category_prompt}\n"
                    f"Visual theme: {theme_prompt}\n"
                    f"User description: {user_input}\n\n"
                    "Write the FLUX prompt:"
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

    # "제품이미지" 라벨
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
    """FLUX.1-schnell NF4로 이미지 생성. 제품 이미지 있으면 PIL 합성."""
    _load_flux_pipeline()

    result = _flux_pipe(
        prompt=prompt,
        num_inference_steps=4,
        guidance_scale=0.0,
        height=512,
        width=512,
    ).images[0]

    if product_image:
        product_img = Image.open(io.BytesIO(product_image))
        result = _composite_product(result, product_img, position)

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()


def write_copy(user_input: str, category: str, history: list) -> str:
    """GPT-5-mini를 사용해 멀티턴 컨텍스트를 반영한 한국어 광고 문구 생성."""
    category_label = CATEGORIES[category]["label"]

    messages = [
        {
            "role": "system",
            "content": (
                f"당신은 {category_label} 업종 소상공인을 위한 광고 카피라이터입니다. "
                "사용자의 요청을 바탕으로 짧고 임팩트 있는 한국어 광고 문구를 2~3줄로 작성하세요. "
                "이전 대화 히스토리가 있다면 피드백을 반영해 개선하세요."
            ),
        }
    ]

    for turn in history:
        messages.append({"role": "user", "content": turn["user_input"]})
        messages.append({"role": "assistant", "content": turn["copy"]})

    messages.append({"role": "user", "content": user_input})

    response = _openai.chat.completions.create(
        model="gpt-5-mini",
        messages=messages,
    )
    return response.choices[0].message.content.strip()


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
    # 손글씨 폰트일 때만 기울기 효과 적용
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
