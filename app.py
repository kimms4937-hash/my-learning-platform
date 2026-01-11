import streamlit as st
import requests
from PyPDF2 import PdfReader
from pptx import Presentation

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="무료 학습 정리 머신", layout="wide")
st.title("📘 무료 학습 정리 머신")
st.markdown("수업 자료를 올리면 핵심만 정리해준다.")

# -----------------------------
# Hugging Face API
# -----------------------------
HF_API_KEY = st.secrets["HF_API_KEY"]
API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-large"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# -----------------------------
# 파일 처리
# -----------------------------
def get_pdf_text(file):
    reader = PdfReader(file)
    return "".join(page.extract_text() or "" for page in reader.pages)

def get_pptx_text(file):
    prs = Presentation(file)
    text = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text

def query(prompt):
    response = requests.post(
        API_URL,
        headers=HEADERS,
        json={"inputs": prompt}
    )
    return response.json()

# -----------------------------
# UI
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    st.header("1. 자료 업로드")
    main_file = st.file_uploader("PDF 또는 PPT", type=["pdf", "pptx"])

with col2:
    st.header("2. 정리 요청")
    style = st.selectbox(
        "정리 방식",
        ["핵심 개념 요약", "시험 대비 정리", "목차형 정리"]
    )
    btn = st.button("🧠 정리 시작")

# -----------------------------
# 실행
# -----------------------------
if btn and main_file:
    with st.spinner("정리 중..."):
        if main_file.name.endswith(".pdf"):
            text = get_pdf_text(main_file)
        else:
            text = get_pptx_text(main_file)

        prompt = f"""
다음 학습 자료를 읽고 "{style}" 형식으로 정리하라.

- 불필요한 말 제거
- 번호와 소제목 사용
- 노트처럼 간결하게 작성

[학습 자료]
{text[:4000]}
"""

        result = query(prompt)

        if isinstance(result, dict) and "error" in result:
            st.error(result["error"])
        else:
            st.success("정리 완료")
            st.write(result[0]["generated_text"])
