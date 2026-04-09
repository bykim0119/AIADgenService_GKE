import io
import json
import base64
import os
import requests
import streamlit as st
from PIL import Image
from categories import CATEGORIES
from themes import THEMES

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="맞춤형 광고 제작 서비스", layout="centered")
st.title("맞춤형 광고 제작 서비스")
st.caption("소상공인을 위한 AI 광고 이미지 & 문구 자동 생성")

# 세션 초기화
if "history" not in st.session_state:
    st.session_state.history = []
if "last_image" not in st.session_state:
    st.session_state.last_image = None
if "last_copy" not in st.session_state:
    st.session_state.last_copy = None

# --- 사이드바: 설정 ---
with st.sidebar:
    st.header("광고 설정")
    category_key = st.selectbox(
        "업종 선택",
        options=list(CATEGORIES.keys()),
        format_func=lambda k: CATEGORIES[k]["label"],
    )
    theme_key = st.selectbox(
        "이미지 스타일",
        options=list(THEMES.keys()),
        format_func=lambda k: THEMES[k]["label"],
    )
    st.divider()
    text_position = st.selectbox(
        "카피 문구 위치",
        options=["top", "bottom", "center"],
        format_func=lambda k: {"top": "상단", "bottom": "하단", "center": "중앙"}[k],
    )
    uploaded_product = st.file_uploader(
        "제품 이미지 첨부 (선택)",
        type=["jpg", "jpeg", "png", "webp"],
        help="첨부 시 제품 외관을 반영한 광고 이미지를 생성합니다.",
    )
    if uploaded_product:
        st.image(uploaded_product, caption="첨부된 제품 이미지", use_container_width=True)
        product_position = st.selectbox(
            "제품 이미지 위치",
            options=["bottom-center", "bottom-left", "bottom-right", "center-left", "center-right"],
            format_func=lambda k: {
                "bottom-center": "하단 중앙",
                "bottom-left":   "하단 좌측",
                "bottom-right":  "하단 우측",
                "center-left":   "중앙 좌측",
                "center-right":  "중앙 우측",
            }[k],
        )
    else:
        product_position = "bottom-center"

# --- 메인: 입력 ---
is_first = len(st.session_state.history) == 0
placeholder = "예) 아메리카노 한 잔으로 시작하는 따뜻한 하루" if is_first else "피드백 또는 새로운 요청을 입력하세요"
user_input = st.text_area("어떤 광고를 만들까요?", placeholder=placeholder, height=100)
generate_btn = st.button("생성하기", type="primary", use_container_width=True)

# --- 생성 ---
if generate_btn:
    if not user_input.strip():
        st.warning("광고 내용을 입력해 주세요.")
    else:
        product_bytes = uploaded_product.read() if uploaded_product else None
        if uploaded_product:
            uploaded_product.seek(0)

        with st.spinner("광고를 제작하는 중입니다..."):
            try:
                files = {}
                if product_bytes:
                    files["product_image"] = ("product.jpg", product_bytes, "image/jpeg")

                resp = requests.post(
                    f"{BACKEND_URL}/generate",
                    data={
                        "user_input": user_input,
                        "category_key": category_key,
                        "theme_key": theme_key,
                        "history": json.dumps(st.session_state.history),
                        "product_position": product_position,
                        "text_position": text_position,
                    },
                    files=files if files else None,
                )
                resp.raise_for_status()
                result = resp.json()

                image_bytes = base64.b64decode(result["image"])
                copy_text = result["copy"]
                sd_prompt = result["sd_prompt"]

                st.session_state.history.append({
                    "turn": len(st.session_state.history) + 1,
                    "user_input": user_input,
                    "sd_prompt": sd_prompt,
                    "copy": copy_text,
                })
                st.session_state.last_image = image_bytes
                st.session_state.last_copy = copy_text

            except Exception as e:
                st.error(f"생성 중 오류가 발생했습니다: {e}")

# --- 결과 표시 ---
if st.session_state.last_image:
    st.divider()
    st.subheader("생성 결과")

    col1, col2 = st.columns([1, 1])
    with col1:
        image = Image.open(io.BytesIO(st.session_state.last_image))
        st.image(image, caption="생성된 광고 이미지", use_container_width=True)
        st.download_button(
            label="이미지 다운로드",
            data=st.session_state.last_image,
            file_name="ad_image.png",
            mime="image/png",
            use_container_width=True,
        )
    with col2:
        st.markdown("**광고 문구**")
        st.info(st.session_state.last_copy)
        st.download_button(
            label="문구 다운로드",
            data=st.session_state.last_copy,
            file_name="ad_copy.txt",
            mime="text/plain",
            use_container_width=True,
        )

# --- 히스토리 ---
if len(st.session_state.history) > 1:
    st.divider()
    with st.expander(f"이전 생성 히스토리 ({len(st.session_state.history)}턴)"):
        for turn in reversed(st.session_state.history[:-1]):
            st.markdown(f"**턴 {turn['turn']}** — {turn['user_input']}")
            st.caption(f"문구: {turn['copy']}")
            st.caption(f"SD 프롬프트: {turn['sd_prompt']}")
            st.divider()

if st.session_state.history:
    if st.button("대화 초기화", use_container_width=True):
        st.session_state.history = []
        st.session_state.last_image = None
        st.session_state.last_copy = None
        st.rerun()
