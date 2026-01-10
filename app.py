# app.py
import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from pptx import Presentation
from fpdf import FPDF
import tempfile
import os
import requests

# ======================================================
# 1. 기본 설정
# ======================================================
st.set_page_config(layout="wide", page_title="AI Learning Hub")

# Gemini API 키
GENAI_API_KEY = st.secrets.get("GENAI_API_KEY")
if not GENAI_API_KEY:
    st.error("GENAI_API_KEY가 설정되지 않았습니다.")
    st.stop()

genai.configure(api_key=GENAI_API_KEY)

# ======================================================
# 2. 한글 폰트 (PDF)
# ======================================================
@st.cache_resource
def get_korean_font():
    font_path = "NanumGothic-Regular.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(font_path, "wb") as f:
            f.write(r.content)
    return font_path

FONT_PATH = get_korean_font()

# ======================================================
# 3. 파일 텍스트 추출
# ======================================================
def get_pdf_text(file_obj):
    text = ""
    try:
        reader = PdfReader(file_obj)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    except Exception as e:
        st.warning(f"PDF 오류: {e}")
    return text

def get_pptx_text(file_obj):
    text = ""
    try:
        prs = Presentation(file_obj)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    text += shape.text + "\n"
    except Exception as e:
        st.warning(f"PPT 오류: {e}")
    return text

# ======================================================
# 4. PDF 생성
# ======================================================
def create_pdf(summary, explanation):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("Nanum", "", FONT_PATH, uni=True)
    pdf.set_font("Nanum", size=12)

    pdf.cell(0, 10, "AI 학습 리포트", ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("Nanum", size=10)
    pdf.cell(0, 8, "[요약 내용]", ln=True)
    pdf.multi_cell(0, 7, summary[:2000] if summary else "내용 없음")
    pdf.ln(4)

    pdf.cell(0, 8, "[AI 설명]", ln=True)
    pdf.multi_cell(0, 7, explanation if explanation else "응답 없음")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp.name)
    return tmp.name

# ======================================================
# 5. UI
# ======================================================
st.title("Ultimate AI Learning Hub")
st.caption("PDF / PPT 기반 AI 학습 도우미")
st.markdown("---")

col1, col2 = st.columns(2)

# --------------------
# 자료 업로드
# --------------------
with col1:
    st.subheader("자료 업로드")
    main_file = st.file_uploader("메인 자료 (PDF)", type=["pdf"])
    supp_file = st.file_uploader("보충 자료 (PDF / PPT)", type=["pdf", "pptx"])

    main_text = ""
    supp_text = ""

    if main_file:
        main_text = get_pdf_text(main_file)
        st.success("메인 자료 로드 완료")

    if supp_file:
        if supp_file.name.endswith(".pdf"):
            supp_text = get_pdf_text(supp_file)
        else:
            supp_text = get_pptx_text(supp_file)
        st.success("보충 자료 로드 완료")

# --------------------
# AI 질문
# --------------------
with col2:
    st.subheader("AI 튜터")
    user_question = st.text_area("질문을 입력하세요", height=120)

    if st.button("설명 요청", type="primary"):
        if not user_question:
            st.warning("질문을 입력하세요.")
        else:
            with st.spinner("AI가 분석 중입니다..."):
