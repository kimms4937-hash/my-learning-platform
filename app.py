import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from pptx import Presentation
from fpdf import FPDF
import tempfile
import os
import time
import requests

# --------------------------------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------------------------------

st.set_page_config(layout="wide", page_title="나만의 AI 학습 사이트")

# API 키 확인
if "GENAI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GENAI_API_KEY"])
else:
    st.error("설정 오류: Streamlit Secrets에 'GENAI_API_KEY'를 등록해주세요.")
    st.stop()

# --------------------------------------------------------------------------
# 2. 한글 폰트 준비
# --------------------------------------------------------------------------

@st.cache_resource
def get_korean_font():
    font_file = "NanumGothic.ttf"
    if not os.path.exists(font_file):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        response = requests.get(url)
        with open(font_file, "wb") as f:
            f.write(response.content)
    return font_file

FONT_PATH = get_korean_font()

# --------------------------------------------------------------------------
# 3. 기능 함수들
# --------------------------------------------------------------------------

def get_pdf_text(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"PDF 텍스트 추출 실패: {e}"

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
        return f"PPT 텍스트 추출 실패: {e}"

def create_pdf_report(original, explanation):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Nanum', '', FONT_PATH, uni=True)
    pdf.set_font('Nanum', size=11)

    pdf.cell(0, 10, "AI 학습 리포트", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font(size=10)
    pdf.cell(0, 10, "[원본 자료 요약]", ln=True)
    pdf.multi_cell(0, 8, original[:5000])

    pdf.ln(5)
    pdf.cell(0, 10, "[AI 설명]", ln=True)
    pdf.multi_cell(0, 8, explanation)

    output_path = tempfile.mktemp(suffix=".pdf")
    pdf.output(output_path)
    return output_path

# --------------------------------------------------------------------------
# 4. 화면 구성
# --------------------------------------------------------------------------

st.title("📚 나만의 영구적인 학습 사이트")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.header("1. 자료 업로드")
    main_file = st.file_uploader("메인 수업 자료 (PDF)", type=["pdf"])
    supp_file = st.file_uploader("보충 자료 (PDF / PPT)", type=["pdf", "pptx"])

with col2:
    st.header("2. AI 튜터")
    question = st.text_area("질문", "이 내용을 바탕으로 핵심 내용을 설명해줘.")

    if st.button("🚀 설명 요청하기"):
        if not main_file:
            st.warning("메인 자료를 업로드하세요.")
        else:
            with st.spinner("AI가 분석 중입니다..."):
                try:
                    prompt_parts = []

                    # 메인 PDF
                    main_text = get_pdf_text(main_file)
                    prompt_parts.append(f"메인 자료:\n{main_text[:30000]}")

                    # 보충 자료
                    if supp_file:
                        if supp_file.name.endswith(".pdf"):
                            supp_text = get_pdf_text(supp_file)
                        else:
                            supp_text = get_pptx_text(supp_file)
                        prompt_parts.append(f"보충 자료:\n{supp_text[:20000]}")

                    # 질문
                    prompt_parts.append(f"요청 사항:\n{question}")

                    prompt = "\n\n".join(prompt_parts)

                    # ✅ 모델 (v1beta에서 유일하게 안정)
                    model = genai.GenerativeModel("models/gemini-pro")
                    response = model.generate_content(prompt)

                    st.session_state["result"] = response.text
                    st.session_state["main_text"] = main_text

                except Exception as e:
                    st.error(f"에러 발생: {e}")

# --------------------------------------------------------------------------
# 5. 결과 출력
# --------------------------------------------------------------------------

if "result" in st.session_state:
    st.success("분석 완료!")
    st.write(st.session_state["result"])

    pdf_path = create_pdf_report(
        st.session_state["main_text"],
        st.session_state["result"]
    )

    with open(pdf_path, "rb") as f:
        st.download_button(
            "📄 PDF로 저장하기",
            f,
            file_name="study_note.pdf"
        )
