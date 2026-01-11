import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from pptx import Presentation
from fpdf import FPDF
import tempfile
import os
import requests

# --------------------------------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------------------------------

st.set_page_config(layout="wide", page_title="나만의 AI 학습 사이트")

# API 키 설정
if "GENAI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GENAI_API_KEY"])
else:
    st.error("Streamlit Secrets에 GENAI_API_KEY가 없습니다.")
    st.stop()

# --------------------------------------------------------------------------
# 2. 한글 폰트
# --------------------------------------------------------------------------

@st.cache_resource
def get_korean_font():
    font_file = "NanumGothic.ttf"
    if not os.path.exists(font_file):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        r = requests.get(url)
        with open(font_file, "wb") as f:
            f.write(r.content)
    return font_file

FONT_PATH = get_korean_font()

# --------------------------------------------------------------------------
# 3. 파일 처리 함수
# --------------------------------------------------------------------------

def get_pdf_text(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"PDF 오류: {e}"

def get_pptx_text(file):
    try:
        prs = Presentation(file)
        text = ""
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
        return text
    except Exception as e:
        return f"PPT 오류: {e}"

def create_pdf_report(original, explanation):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("Nanum", "", FONT_PATH, uni=True)
    pdf.set_font("Nanum", size=11)

    pdf.cell(0, 10, "AI 학습 리포트", ln=True, align="C")
    pdf.ln(8)

    pdf.set_font(size=10)
    pdf.cell(0, 8, "[원본 요약]", ln=True)
    pdf.multi_cell(0, 7, original[:4000])

    pdf.ln(4)
    pdf.cell(0, 8, "[AI 설명]", ln=True)
    pdf.multi_cell(0, 7, explanation)

    path = tempfile.mktemp(suffix=".pdf")
    pdf.output(path)
    return path

# --------------------------------------------------------------------------
# 4. UI
# --------------------------------------------------------------------------

st.title("📚 나만의 AI 학습 사이트")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.header("1. 자료 업로드")
    main_file = st.file_uploader("메인 PDF", type=["pdf"])
    supp_file = st.file_uploader("보충 자료 (PDF/PPT)", type=["pdf", "pptx"])

with col2:
    st.header("2. AI 튜터")
    question = st.text_area("질문", "이 내용을 바탕으로 핵심을 설명해줘.")

    if st.button("🚀 설명 요청하기"):
        if not main_file:
            st.warning("메인 PDF를 업로드하세요.")
        else:
            with st.spinner("AI 분석 중..."):
                try:
                    parts = []

                    main_text = get_pdf_text(main_file)
                    parts.append(f"메인 자료:\n{main_text[:30000]}")

                    if supp_file:
                        if supp_file.name.endswith(".pdf"):
                            supp_text = get_pdf_text(supp_file)
                        else:
                            supp_text = get_pptx_text(supp_file)
                        parts.append(f"보충 자료:\n{supp_text[:20000]}")

                    parts.append(f"요청:\n{question}")
                    prompt = "\n\n".join(parts)

                    # ✅ v1beta에서 실제로 동작하는 모델
                    model = genai.GenerativeModel("models/text-bison-001")
                    response = model.generate_content(prompt)

                    st.session_state["result"] = response.text
                    st.session_state["main_text"] = main_text

                except Exception as e:
                    st.error(f"에러 발생: {e}")

# --------------------------------------------------------------------------
# 5. 결과
# --------------------------------------------------------------------------

if "result" in st.session_state:
    st.success("완료!")
    st.write(st.session_state["result"])

    pdf_path = create_pdf_report(
        st.session_state["main_text"],
        st.session_state["result"]
    )

    with open(pdf_path, "rb") as f:
        st.download_button("📄 PDF 저장", f, file_name="study_note.pdf")
