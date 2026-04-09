import json
import base64
from fastapi import FastAPI, UploadFile, File, Form
from celery_app import celery_app

app = FastAPI(title="광고 생성 API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
async def generate(
    user_input: str = Form(...),
    category_key: str = Form(...),
    theme_key: str = Form(...),
    history: str = Form("[]"),
    product_image: UploadFile = File(None),
    product_position: str = Form("bottom-center"),
    text_position: str = Form("top"),
    font_name: str = Form("nanumpen"),
    text_color: str = Form("#FFF5B4"),
    font_size_ratio: float = Form(0.052),
):
    history_list = json.loads(history)
    product_bytes = await product_image.read() if product_image else None
    product_image_b64 = base64.b64encode(product_bytes).decode() if product_bytes else None

    task = celery_app.send_task(
        "tasks.generate_ad",
        args=[
            user_input, category_key, theme_key, history_list,
            product_image_b64, product_position, text_position,
            font_name, text_color, font_size_ratio,
        ],
    )
    return {"job_id": task.id}


@app.get("/status/{job_id}")
async def status(job_id: str):
    result = celery_app.AsyncResult(job_id)

    if result.state == "PENDING":
        return {"status": "pending"}
    elif result.state == "STARTED":
        return {"status": "processing"}
    elif result.state == "SUCCESS":
        return {"status": "done", **result.result}
    elif result.state == "FAILURE":
        return {"status": "error", "detail": str(result.result)}
    return {"status": result.state.lower()}
