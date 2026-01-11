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
# 1. 기본 설정 및 한글 폰트 준비 (깨짐 방지)
# --------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="나만의 AI 학습 사이트")

# API 키 확인
if "GENAI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets)
else:
    st.error("설정 오류: Streamlit Secrets에 'GENAI_API_KEY'를 등록해주세요.")

# 한글 폰트 다운로드 (서버에 폰트가 없으므로 매번 다운로드)
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
# 2. 기능 함수들
# --------------------------------------------------------------------------

def get_pdf_text(file):
    text = ""
    try:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    except:
        return "PDF 텍스트 추출 실패"
    return text

def get_pptx_text(file):
    text = ""
    try:
        prs = Presentation(file)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
    except:
        return "PPT 텍스트 추출 실패"
    return text

def upload_media(file):
    # 파일을 임시 저장 후 업로드
    suffix = os.path.splitext(file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.getvalue())
        tmp_path = tmp.name
    
    uploaded_file = genai.upload_file(tmp_path)
    
    # 처리 대기
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        uploaded_file = genai.get_file(uploaded_file.name)
        
    return uploaded_file

def create_pdf_report(original, explanation):
    pdf = FPDF()
    pdf.add_page()
    
    # 한글 폰트 적용
    pdf.add_font('Nanum', '', FONT_PATH, uni=True)
    pdf.set_font('Nanum', size=11)
    
    # 제목
    pdf.cell(0, 10, txt="AI 학습 리포트", ln=True, align='C')
    pdf.ln(10)
    
    # 원본 요약
    pdf.set_font('Nanum', size=10)
    pdf.cell(0, 10, txt="[원본 자료 요약]", ln=True)
    pdf.multi_cell(0, 8, txt=original[:1000] + "...") # 너무 길면 자름
    pdf.ln(5)
    
    # AI 설명
    pdf.cell(0, 10, txt="[AI 상세 설명]", ln=True)
    pdf.multi_cell(0, 8, txt=explanation)
    
    # 파일 저장
    output_path = tempfile.mktemp(suffix=".pdf")
    pdf.output(output_path)
    return output_path

# --------------------------------------------------------------------------
# 3. 화면 구성
# --------------------------------------------------------------------------

st.title("📚 나만의 영구적인 학습 사이트")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.header("1. 자료 업로드")
    main_file = st.file_uploader("메인 수업 자료 (PDF)", type=["pdf"])
    supp_file = st.file_uploader("보충 자료 (PPT, 영상, 음성 등)", type=["pdf", "pptx", "mp4", "mp3", "wav"])

with col2:
    st.header("2. AI 튜터")
    question = st.text_area("질문 또는 요청사항", "이 내용을 바탕으로 핵심 내용을 설명해줘.")
    
    if st.button("🚀 설명 요청하기"):
        if not main_file:
            st.warning("메인 자료를 먼저 올려주세요.")
        else:
            with st.status("AI가 분석 중입니다..."):
                try:
                    # 모델 설정
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # [중요] 여기가 계속 에러나던 부분입니다. 확실하게 수정했습니다.
                    prompt_parts = 
                    
                    # 1. 메인 자료 텍스트 추가
                    main_text = get_pdf_text(main_file)
                    prompt_parts.append(f"메인 자료 내용:\n{main_text[:30000]}")
                    
                    # 2. 보충 자료 처리
                    if supp_file:
                        ftype = supp_file.name.split('.')[-1].lower()
                        if ftype == 'pdf':
                            supp_text = get_pdf_text(supp_file)
                            prompt_parts.append(f"보충 자료 내용:\n{supp_text[:20000]}")
                        elif ftype in ['pptx', 'ppt']:
                            supp_text = get_pptx_text(supp_file)
                            prompt_parts.append(f"보충 자료 내용:\n{supp_text[:20000]}")
                        else: # 영상/음성
                            st.write("영상/음성 파일 업로드 중...")
                            media = upload_media(supp_file)
                            prompt_parts.append(media)
                            prompt_parts.append("위 미디어 파일을 참고하세요.")
                    
                    # 3. 질문 추가
                    prompt_parts.append(f"요청 사항: {question}")
                    
                    # 4. 실행
                    st.write("답변 생성 중...")
                    response = model.generate_content(prompt_parts)
                    st.session_state['result'] = response.text
                    st.session_state['main_text'] = main_text
                    
                except Exception as e:
                    st.error(f"에러 발생: {e}")

    # 결과가 있으면 보여주기
    if 'result' in st.session_state:
        st.success("분석 완료!")
        st.write(st.session_state['result'])
        
        # PDF 다운로드 버튼
        pdf_file = create_pdf_report(st.session_state['main_text'], st.session_state['result'])
        with open(pdf_file, "rb") as f:
            st.download_button("📄 PDF로 저장하기", f, "study_note.pdf")
