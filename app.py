# app.py
import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from pptx import Presentation
from fpdf import FPDF
import tempfile
import os
import time
import requests
from io import BytesIO

# -----------------------
# 기본 설정
# -----------------------
st.set_page_config(layout="wide", page_title="나만의 AI 학습 플랫폼")

# API 키 설정 (Streamlit Secrets 사용)
try:
    GENAI_API_KEY = st.secrets.get("GENAI_API_KEY")
    if GENAI_API_KEY:
        genai.configure(api_key=GENAI_API_KEY)
    else:
        st.error("API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")
except Exception as e:
    st.error(f"API 키 설정 중 오류 발생: {e}")

# 한글 폰트 다운로드/캐시
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

# -----------------------
# 자료 처리 함수들
# -----------------------
def get_pdf_text(file_obj) -> str:
    """UploadedFile 또는 파일 경로를 받아 텍스트를 추출합니다."""
    text = ""
    try:
        # streamlit UploadedFile은 file-like이므로 바로 전달 가능
        reader = PdfReader(file_obj)
        for page in reader.pages:
            ptext = page.extract_text()
            if ptext:
                text += ptext + "\n"
    except Exception as e:
        st.warning(f"PDF 텍스트 추출 오류: {e}")
    return text

def get_pptx_text(file_obj) -> str:
    text = ""
    try:
        # Presentation은 파일 경로나 file-like 모두 지원
        prs = Presentation(file_obj)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    text += shape.text + "\n"
    except Exception as e:
        st.warning(f"PPTX 텍스트 추출 오류: {e}")
    return text

def upload_to_gemini(file_obj, mime_type, max_wait=60):
    """
    파일을 임시로 저장한 뒤 genai.upload_file로 업로드.
    처리 상태가 PROCESSING이면 폴링하되 max_wait 초를 넘기면 TimeoutError 발생.
    """
    suffix = f".{mime_type.split('/')[-1]}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_obj.getvalue())
        tmp_path = tmp.name

    # 업로드
    uploaded = genai.upload_file(tmp_path, mime_type=mime_type)
    start = time.time()
    # 상태가 PROCESSING이면 폴링
    while getattr(uploaded, "state", None) and getattr(uploaded.state, "name", "") == "PROCESSING":
        if time.time() - start > max_wait:
            try:
                os.remove(tmp_path)
            except:
                pass
            raise TimeoutError("파일 처리 대기 시간이 초과되었습니다.")
        time.sleep(2)
        uploaded = genai.get_file(uploaded.name)

    # tmp 파일 제거 (로컬에 남기지 않음)
    try:
        os.remove(tmp_path)
    except:
        pass

    return uploaded

def create_pdf(original_summary: str, ai_explanation: str) -> str:
    pdf = FPDF()
    pdf.add_page()
    # 유니코드 폰트 등록
    pdf.add_font('Nanum', '', FONT_PATH, uni=True)
    pdf.set_font('Nanum', size=12)

    pdf.cell(200, 10, txt="AI 학습 리포트", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font('Nanum', size=10)
    pdf.cell(200, 10, txt="[요약 내용]", ln=True)
    pdf.multi_cell(0, 8, txt=(original_summary[:2000] + "...") if original_summary else "내용 없음")
    pdf.ln(6)

    pdf.cell(200, 10, txt="[AI 상세 설명]", ln=True)
    pdf.multi_cell(0, 8, txt=ai_explanation if ai_explanation else "응답 없음")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmpf:
        pdf.output(tmpf.name)
        return tmpf.name

# -----------------------
# UI (메인)
# -----------------------
st.title("⚡️ Ultimate A
