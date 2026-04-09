# Architecture

## 시스템 아키텍처

```mermaid
flowchart TD
    Browser["브라우저"]

    subgraph GKE["GKE Cluster"]
        FE["Frontend\nnginx + React · LoadBalancer"]
        BE["Backend\nFastAPI · no GPU"]
        RD[("Redis\nbroker + backend")]

        subgraph CPU["CPU Node (e2-small)"]
            WK["Celery Worker\nrembg · overlay · comfyui_client"]
        end

        subgraph GPU["GPU Node (T4 Spot)"]
            CUI["ComfyUI\nSDXL + IP-Adapter · port 8188"]
        end
    end

    OAI["OpenAI API\nGPT-5-mini"]
    PVC[("PVC\nSDXL 모델 + IP-Adapter\n~10 GB")]

    Browser -- "① POST /api/generate" --> FE
    Browser -- "③ GET /api/status/{job_id} (2초 폴링)" --> FE
    FE -- "proxy" --> BE
    BE -- "② send_task() → job_id 반환" --> RD
    RD -- "태스크 전달" --> WK
    WK -- "결과 저장 (TTL 1h)" --> RD
    WK -- "build_sd_prompt\nwrite_copy" --> OAI
    WK -- "④ POST /prompt\n⑤ GET /history/{id}\n⑥ GET /view" --> CUI
    CUI -- "모델 로드" --> PVC
```

---

## 이미지 생성 파이프라인

```mermaid
flowchart TD
    IN["user_input · category · theme\nproduct_image (optional)"]

    subgraph GPT["OpenAI API (GPT-5-mini)"]
        P1["build_sd_prompt()\n→ 영문 SDXL 프롬프트"]
        P2["write_copy()\n→ 한국어 광고 문구 (멀티턴)"]
    end

    subgraph COMFY["ComfyUI Service (GPU pod · port 8188)"]
        WF["SDXL Workflow\nDreamShaper XL · 30 steps · 1024×1024"]
        IPA["IP-Adapter Advanced\nViT-H · scale=0.5"]
    end

    PROD{"product_image?"}

    REMBG["rembg  CPU\n배경 제거 · 소프트 엣지 · 그림자 합성"]

    OVERLAY["overlay_copy_on_image()\n그라데이션 · 나눔 폰트 5종\n아웃라인 자동 보정"]

    OUT["PNG → base64\nRedis 저장 (TTL 1h)"]

    IN --> P1
    IN --> P2
    P1 --> WF
    WF --> IPA
    IPA --> PROD
    PROD -- "Yes" --> REMBG
    REMBG --> OVERLAY
    PROD -- "No" --> OVERLAY
    P2 --> OVERLAY
    OVERLAY --> OUT
```

---

## VRAM 구성 (T4 14.56 GB · ComfyUI 관리)

```mermaid
block-beta
  columns 1
  block:VRAM["T4 VRAM (14.56 GB)"]
    A["SDXL UNet  fp16  ~5.0 GB"]
    B["CLIP-L + OpenCLIP-G  텍스트 인코더  ~1.4 GB"]
    C["VAE  fp16  ~0.3 GB"]
    D["IP-Adapter ViT-H 가중치  ~1.0 GB"]
    E["ComfyUI 런타임  ~0.5 GB"]
  end
  block:CPU["CPU RAM (Celery Worker)"]
    F["rembg ONNX  CPUExecutionProvider"]
    G["Pillow 텍스트 오버레이"]
  end
```

ComfyUI `model_management.py`가 자동으로 모델 로드/언로드 관리. 총 사용 ~8.2 GB, 여유 ~6 GB.

---

## ComfyUI 워크플로우 구조

### 기본 (제품 이미지 없음)

```
[1] CheckpointLoaderSimple (dreamshaper_xl.safetensors)
        ├── CLIP → [2] CLIPTextEncode (positive prompt)
        ├── CLIP → [3] CLIPTextEncode (negative prompt)
        ├── MODEL → [6] KSampler
        └── VAE   → [7] VAEDecode → [8] SaveImage
[4] EmptyLatentImage (1024×1024) → [6] KSampler
```

### IP-Adapter 포함 (제품 이미지 있음)

```
[1] CheckpointLoaderSimple
        └── [9] IPAdapterModelLoader + [10] CLIPVisionLoader + [11] LoadImage
                └── [12] IPAdapterAdvanced (weight=0.5)
                        └── MODEL → [6] KSampler → [7] VAEDecode → [8] SaveImage
```

KSampler 파라미터: `steps=30`, `cfg=7.5`, `euler_ancestral`, `karras`, `denoise=1.0`

---

## 접근 제어

| 서비스 | 노출 방식 | 비고 |
|--------|-----------|------|
| Frontend | LoadBalancer (공개) | 사용자 접점 |
| Backend (FastAPI) | ClusterIP | Frontend → Backend 내부 통신 |
| Worker | 없음 (Celery 소비) | Redis 큐 구독 |
| ComfyUI | ClusterIP (port 8188) | Worker에서만 접근, 외부 미노출 |
| Redis | ClusterIP | Backend ↔ Worker 브로커 |

ComfyUI GUI 디버깅 시: `kubectl port-forward deployment/comfyui 8188:8188`
