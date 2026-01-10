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
st.set_page_config(layout="wide", page_title="나만의 AI 학습 플랫폼")

# API 키 설정
try:
    GENAI_API_KEY = st.secrets.get("GENAI_API_KEY")
    if GENAI_API_KEY:
        genai.configure(api_key=GENAI_API_KEY)
    else:
        st.error("API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")
except Exception as e:
    st.error(f"API 키 설정 중 오류 발생: {e}")

# 한글 폰트 (PDF 깨짐 방지)
@st.cache_resource
def get_korean_font():
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        response = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    return font_path

FONT_PATH = get_korean_font()

# --------------------------------------------------------------------------
# 2. 자료 처리 함수들
# --------------------------------------------------------------------------

def get_pdf_text(pdf_file):
    text = ""
    try:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
    except:
        pass
    return text

def get_pptx_text(pptx_file):
    text = ""
    try:
        prs = Presentation(pptx_file)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
    except:
        pass
    return text

def upload_to_gemini(file_obj, mime_type):
    suffix = f".{mime_type.split('/')[-1]}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_obj.getvalue())
        tmp_path = tmp.name
    
    uploaded_file = genai.upload_file(tmp_path, mime_type=mime_type)
    
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        uploaded_file = genai.get_file(uploaded_file.name)
        
    return uploaded_file

def create_pdf(original_summary, ai_explanation):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Nanum', '', FONT_PATH, uni=True)
    pdf.set_font('Nanum', size=12)
    
    pdf.cell(200, 10, txt="AI 학습 리포트", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font('Nanum', size=10)
    pdf.cell(200, 10, txt="[요약 내용]", ln=True)
    pdf.multi_cell(0, 8, txt=original_summary[:2000] + "...") 
    pdf.ln(10)
    
    pdf.cell(200, 10, txt="[AI 상세 설명]", ln=True)
    pdf.multi_cell(0, 8, txt=ai_explanation)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        return tmp_file.name

# --------------------------------------------------------------------------
# 3. 메인 화면 로직
# --------------------------------------------------------------------------

st.title("⚡️ Ultimate AI Learning Hub")
st.caption("지원: PDF, PPT, 동영상, 음성 | 모델: Gemini 1.5 Flash")
st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📂 자료 업로드")
    main_file = st.file_uploader("1. 메인 수업 자료 (PDF 필수)", type=['pdf'], key="main")
    supp_file = st.file_uploader("2. 보충 자료 (PPT/영상/음성)", type=['pdf', 'pptx', 'mp4', 'mp3', 'wav'], key="supp")

    main_text = ""
    supp_content = None 
    supp_type = "none"

    if main_file:
        main_text = get_pdf_text(main_file)
        st.success(f"✅ 메인 자료 확인됨")

    if supp_file:
        ext = supp_file.name.split('.')[-1].lower()
        if ext == 'pdf':
            supp_content = get_pdf_text(supp_file)
            supp_type = "text"
            st.success("✅ 보충 PDF 확인됨")
        elif ext in ['pptx', 'ppt']:
            supp_content = get_pptx_text(supp_file)
            supp_type = "text"
            st.success("✅ 보충 PPT 확인됨")
        elif ext in ['mp4', 'mp3', 'wav']:
            supp_type = "media"
            st.info(f"🎞️ {ext} 미디어 파일 준비됨")

with col2:
    st.subheader("🤖 AI 튜터")
    user_question = st.text_area("질문을 입력하세요", height=100)
    
    if st.button("🚀 설명 요청하기", type="primary"):
        if not main_file and not user_question:
            st.warning("메인 자료와 질문을 입력해주세요.")
        else:
            with st.status("⚡️ AI가 분석 중입니다...", expanded=True) as status:
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # ▼▼▼▼▼ [수정됨] 대괄호를 정확히 넣었습니다 ▼▼▼▼▼
                    prompt_parts =
                    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
                    
                    prompt_parts.append("당신은 친절한 AI 튜터입니다. 다음 자료를 보고 질문에 답하세요.")
                    
                    if main_text:
                        prompt_parts.append(f"Answer based on this main text:\n{main_text[:30000]}")
                    
                    if supp_file:
                        st.write("📂 보충 자료 읽는 중...")
                        if supp_type == "text":
                            prompt_parts.append(f"Also consider this text:\n{supp_content[:20000]}")
                        elif supp_type == "media":
                            mime = "video/mp4" if "mp4" in supp_file.name else "audio/mp3"
                            media_file = upload_to_gemini(supp_file, mime)
                            prompt_parts.append(media_file)
                            prompt_parts.append("Analyze the media file above.")
                    
                    prompt_parts.append(f"Question: {user_question}")
                    
                    st.write("✍️ 답변 작성 중...")
                    response_container = st.empty()
                    full_response = ""
                    
                    response = model.generate_content(prompt_parts, stream=True)
                    for chunk in response:
                        if chunk.text:
                            full_response += chunk.text
                            response_container.markdown(full_response)
                            
                    st.session_state.ai_response = full_response
                    status.update(label="✅ 완료!", state="complete", expanded=False)
                    
                except Exception as e:
                    st.error(f"에러 발생: {e}")
                    status.update(label="❌ 실패", state="error")

    if "ai_response" in st.session_state and st.session_state.ai_response:
        st.markdown("---")
        if st.button("📄 PDF로 결과 저장"):
            pdf_path = create_pdf(main_text if main_text else "내용 없음", st.session_state.ai_response)
            with open(pdf_path, "rb") as f:
                st.download_button("다운로드", f, file_name="study_note.pdf")
            os.remove(pdf_path)
