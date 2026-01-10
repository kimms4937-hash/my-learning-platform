import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from fpdf import FPDF
import tempfile
import os

# --------------------------------------------------------------------------
# 1. 기본 설정 및 Gemini API 초기화 (속도 개선 버전)
# --------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="나만의 AI 학습 플랫폼 (Fast)")

try:
    GENAI_API_KEY = st.secrets
    genai.configure(api_key=GENAI_API_KEY)
except Exception:
    st.error("API 키 설정 오류: Streamlit Secrets에 'GENAI_API_KEY'가 있는지 확인하세요.")

# --------------------------------------------------------------------------
# 2. 헬퍼 함수 (PDF 생성 및 텍스트 추출)
# --------------------------------------------------------------------------

def get_pdf_text(pdf_file):
    """PDF 파일에서 텍스트를 추출하는 함수"""
    text = ""
    pdf_reader = PdfReader(pdf_file)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def create_pdf(original_text, ai_explanation):
    """결과물을 PDF로 저장하는 함수"""
    pdf = FPDF()
    pdf.add_page()
    # 한글 폰트가 없으면 깨질 수 있으므로 영문 기본 폰트 사용 (한글 폰트 적용 시 수정 필요)
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Learning Report", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10, style='B')
    pdf.cell(200, 10, txt="Summary of Materials:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=original_text[:1000] + "...") 
    pdf.ln(5)
    
    pdf.set_font("Arial", size=10, style='B')
    pdf.cell(200, 10, txt="AI Explanation:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=ai_explanation)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        return tmp_file.name

# --------------------------------------------------------------------------
# 3. 메인 화면 구성
# --------------------------------------------------------------------------

st.title("⚡️ Fast AI Learning Hub")
st.caption("Gemini 1.5 Flash 모델을 사용하여 속도가 훨씬 빨라졌습니다.")
st.markdown("---")

col1, col2 = st.columns([1, 1])

# [왼쪽] 자료 업로드 구역 (메인 + 보충)
with col1:
    st.subheader("📂 학습 자료 업로드")
    
    # 1. 메인 수업 자료
    st.markdown("**1. 메인 수업 자료 (필수)**")
    main_file = st.file_uploader("수업 PDF, 동영상, 음성 파일", type=['pdf', 'mp4', 'mp3'], key="main")
    
    # 2. 보충 자료 (새로 추가된 기능!)
    st.markdown("**2. 보충 자료 (선택)**")
    supp_file = st.file_uploader("참고할 추가 PDF 자료가 있다면 올려주세요", type=['pdf'], key="supp")

    # 텍스트 추출 변수 초기화
    main_text = ""
    supp_text = ""

    # 메인 파일 처리
    if main_file:
        if main_file.type == "application/pdf":
            main_text = get_pdf_text(main_file)
            st.success(f"메인 자료 로드 완료 ({len(main_text)}자)")
        else:
            st.info("동영상/음성 파일은 재생만 가능하며, 내용은 AI가 직접 분석하지 못할 수 있습니다 (텍스트 요약 불가능).")
            st.video(main_file) if main_file.type == 'video/mp4' else st.audio(main_file)

    # 보충 파일 처리
    if supp_file:
        supp_text = get_pdf_text(supp_file)
        st.success(f"보충 자료 로드 완료 ({len(supp_text)}자)")

# [오른쪽] AI 분석 구역
with col2:
    st.subheader("🤖 AI 튜터")
    
    user_question = st.text_area("질문 또는 요청사항 (예: 이 내용을 요약해줘)", height=100)
    
    if st.button("🚀 설명 요청하기 (Fast)"):
        if not main_file and not user_question:
            st.warning("자료를 올리거나 질문을 입력해주세요.")
        else:
            # 프롬프트 구성 (메인 + 보충 자료 결합)
            full_prompt = f"""
            당신은 유능한 AI 튜터입니다. 아래 자료들을 바탕으로 사용자의 질문에 답하세요.
            
            [메인 수업 자료 내용]:
            {main_text[:10000]} 
            
            [보충 참고 자료 내용]:
            {supp_text[:10000] if supp_text else "(없음)"}
            
            [사용자 질문]:
            {user_question}
            
            내용을 종합하여 이해하기 쉽게 설명해주세요.
            """
            
            # 스트리밍 방식으로 출력 (속도 향상 체감)
            try:
                # 모델 변경: gemini-pro -> gemini-1.5-flash (속도 10배 향상)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # 실시간으로 글자가 찍히도록 설정 (stream=True)
                response_container = st.empty()
                full_response = ""
                
                response = model.generate_content(full_prompt, stream=True)
                
                for chunk in response:
                    full_response += chunk.text
                    response_container.markdown(full_response)
                
                # 결과 저장 (PDF 생성을 위해)
                st.session_state.ai_response = full_response
                
            except Exception as e:
                st.error(f"에러 발생: {e}")

    # PDF 다운로드 버튼
    if "ai_response" in st.session_state and st.session_state.ai_response:
        st.markdown("---")
        if st.button("📄 결과물 PDF로 저장"):
            pdf_path = create_pdf(main_text if main_text else "Media File", st.session_state.ai_response)
            with open(pdf_path, "rb") as f:
                st.download_button("다운로드 시작", f, file_name="study_note.pdf")
            os.remove(pdf_path)
