import base64
from celery.utils.log import get_task_logger
from celery_app import celery_app
from pipeline_sdxl import build_sd_prompt, write_copy, overlay_copy_on_image
from comfyui_client import generate_image

logger = get_task_logger(__name__)


@celery_app.task(bind=True, name="tasks.generate_ad")
def generate_ad(
    self,
    user_input,
    category_key,
    theme_key,
    history,
    product_image_b64,
    product_position,
    text_position,
    font_name,
    text_color,
    font_size_ratio,
):
    product_bytes = base64.b64decode(product_image_b64) if product_image_b64 else None

    sd_prompt = build_sd_prompt(user_input, category_key, theme_key)
    logger.warning(f"[SD_PROMPT] {sd_prompt}")
    copy_result = write_copy(user_input, category_key, history)
    copy_text = copy_result["copy"]
    message = copy_result["message"]

    # 이미지 생성: ComfyUI API 호출 (product_position은 IP-Adapter 방식에서 미사용)
    image_bytes = generate_image(sd_prompt, product_bytes)

    image_bytes = overlay_copy_on_image(
        image_bytes, copy_text, text_position, font_name, text_color, font_size_ratio
    )

    return {
        "image": base64.b64encode(image_bytes).decode(),
        "copy": copy_text,
        "message": message,
        "sd_prompt": sd_prompt,
    }
