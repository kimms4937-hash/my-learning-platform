import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from pptx import Presentation
from fpdf import FPDF
import tempfile
import os
import time

# --------------------------------------------------------------------------
# 1. 기본 설정 (속도 중심: Gemini 1.5 Flash)
# --------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="나만의 AI 학습 플랫폼 (Multi-Format)")

try:
    GENAI_API_KEY = st.secrets.get("GENAI_API_KEY")
    if GENAI_API_KEY:
        genai.configure(api_key=GENAI_API_KEY)
    else:
        st.error("API 키가 설정되지 않았습니다. Streamlit Secrets를 확인해주세요.")
except Exception as e:
    st.error(f"API 키 설정 중 오류 발생: {e}")

# --------------------------------------------------------------------------
# 2. 자료 처리 함수들 (PDF, PPT, Media)
# --------------------------------------------------------------------------

def get_pdf_text(pdf_file):
    """PDF에서 텍스트 추출"""
    text = ""
    try:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        st.error(f"PDF 읽기 오류: {e}")
    return text

def get_pptx_text(pptx_file):
    """PPT 파일에서 텍스트 추출"""
    text = ""
    try:
        prs = Presentation(pptx_file)
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
    except Exception as e:
        st.error(f"PPT 읽기 오류: {e}")
    return text

def upload_to_gemini(file_obj, mime_type):
    """동영상/음성 파일을 Gemini 서버로 업로드"""
    # 임시 파일로 저장
    suffix = f".{mime_type.split('/')[-1]}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_obj.getvalue())
        tmp_path = tmp.name
    
    # Gemini 서버로 업로드
    uploaded_file = genai.upload_file(tmp_path, mime_type=mime_type)
    
    # 처리가 완료될 때까지 대기 (Active 상태 확인)
    while uploaded_file.state.name == "PROCESSING":
        time.sleep(2)
        uploaded_file = genai.get_file(uploaded_file.name)
        
    return uploaded_file

def create_pdf(original_summary, ai_explanation):
    """결과 PDF 생성 (한글 깨짐 방지 처리 없음 - 영문 권장)"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Learning Report (Gemini 1.5 Flash)", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10, style='B')
    pdf.cell(200, 10, txt="Input Summary:", ln=True)
    pdf.set_font("Arial", size=10)
    
    # 텍스트가 너무 길 경우를 대비해 일부만 요약
    safe_summary = original_summary[:1000].encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=safe_summary + "...") 
    pdf.ln(5)
    
    pdf.set_font("Arial", size=10, style='B')
    pdf.cell(200, 10, txt="AI Explanation:", ln=True)
    pdf.set_font("Arial", size=10)
    
    safe_explanation = ai_explanation.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=safe_explanation)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        return tmp_file.name

# --------------------------------------------------------------------------
# 3. 메인 UI 및 로직
# --------------------------------------------------------------------------

st.title("⚡️ Ultimate AI Learning Hub")
st.caption("지원 포맷: PDF, PPT, 동영상(MP4), 음성(MP3) | 모델: Gemini 1.5 Flash")
st.markdown("---")

col1, col2 = st.columns([1, 1])

# [왼쪽] 업로드 구역
with col1:
    st.subheader("📂 자료 업로드")
    
    st.markdown("**1. 메인 수업 자료 (필수 - PDF)**")
    main_file = st.file_uploader("수업 자료", type=['pdf'], key="main")
    
    st.markdown("**2. 보충 자료 (선택 - 다양한 포맷)**")
    supp_file = st.file_uploader(
        "참고용 PDF, PPT, 동영상, 음성 파일", 
        type=['pdf', 'pptx', 'mp4', 'mp3', 'wav'], 
        key="supp"
    )

    # 자료 처리 변수
    main_text = ""
    supp_content = None 
    supp_type = "none"

    if main_file:
        main_text = get_pdf_text(main_file)
        st.success(f"✅ 메인 자료 로드 완료")

    if supp_file:
        file_type = supp_file.name.split('.')[-1].lower()
        
        if file_type == 'pdf':
            supp_content = get_pdf_text(supp_file)
            supp_type = "text"
            st.success("✅ 보충 PDF 로드 완료")
            
        elif file_type in ['pptx', 'ppt']:
            supp_content = get_pptx_text(supp_file)
            supp_type = "text"
            st.success("✅ 보충 PPT 텍스트 추출 완료")
            
        elif file_type in ['mp4', 'mp3', 'wav']:
            supp_type = "media"
            st.info(f"🎞️ {file_type} 파일이 감지되었습니다. '설명 요청' 시 분석됩니다.")

# [오른쪽] AI 분석 구역
with col2:
    st.subheader("🤖 AI 튜터 (Fast)")
    
    user_question = st.text_area("질문 입력 (예: 이 내용을 요약해줘)", height=100)
    
    if st.button("🚀 설명 요청하기", type="primary"):
        if not main_file and not user_question:
            st.warning("메인 자료를 올리거나 질문을 입력해주세요.")
        else:
            with st.status("⚡️ AI가 자료를 분석 중입니다...", expanded=True) as status:
                try:
                    # 모델 준비
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # [수정됨] 대괄호를 사용하여 빈 리스트를 올바르게 생성
                    prompt_parts =
                    
                    # 1. 프롬프트 기본 설정
                    system_prompt = "당신은 빠르고 정확한 AI 튜터입니다. 제공된 자료를 바탕으로 사용자의 질문에 답하세요."
                    prompt_parts.append(system_prompt)
                    
                    # 2. 메인 자료 추가
                    if main_text:
                        prompt_parts.append(f"Answer based on this main text:\n{main_text[:30000]}")
                    
                    # 3. 보충 자료 추가
                    if supp_file:
                        st.write("📂 보충 자료 처리 중...")
                        if supp_type == "text":
                            prompt_parts.append(f"Also consider this supplementary text:\n{supp_content[:20000]}")
                        elif supp_type == "media":
                            # 미디어 업로드 처리
                            mime = "video/mp4" if "mp4" in supp_file.name else "audio/mp3"
                            media_file = upload_to_gemini(supp_file, mime)
                            prompt_parts.append(media_file) # 파일 객체 직접 추가
                            prompt_parts.append("Analyze the media file above.")
                    
                    # 4. 사용자 질문 추가
                    prompt_parts.append(f"User Question: {user_question}")
                    
                    # 5. 답변 생성
                    st.write("✍️ 답변 생성 중...")
                    response_container = st.empty()
                    full_response = ""
                    
                    # 스트리밍 출력
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

    # PDF 다운로드
    if "ai_response" in st.session_state and st.session_state.ai_response:
        st.markdown("---")
        if st.button("📄 결과물 PDF로 저장"):
            pdf_path = create_pdf(main_text if main_text else "Media/PPT Content", st.session_state.ai_response)
            with open(pdf_path, "rb") as f:
                st.download_button("다운로드 시작", f, file_name="study_note_fast.pdf")
            os.remove(pdf_path)
