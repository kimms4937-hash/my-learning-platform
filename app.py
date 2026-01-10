import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from fpdf import FPDF
import tempfile
import os

# --------------------------------------------------------------------------
# 1. 기본 설정 및 Gemini API 초기화
# --------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="나만의 AI 학습 플랫폼")

# Streamlit Secrets에서 API 키를 가져옵니다 (보안 설정)
# 로컬 테스트 시에는 st.secrets 대신 직접 키를 입력하는 방식도 가능하지만, 
# 배포를 위해 Secrets 사용을 권장합니다.
try:
    GENAI_API_KEY = st.secrets
    genai.configure(api_key=GENAI_API_KEY)
except Exception:
    st.error("API 키가 설정되지 않았습니다. Streamlit 설정을 확인해주세요.")

# --------------------------------------------------------------------------
# 2. 헬퍼 함수 정의 (기능 구현)
# --------------------------------------------------------------------------

def get_gemini_response(input_text, prompt):
    """Gemini에게 질문하고 답을 받는 함수"""
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt + input_text)
    return response.text

def create_pdf(original_text, ai_explanation):
    """학습 내용과 AI 설명을 합쳐서 PDF로 만드는 함수"""
    pdf = FPDF()
    pdf.add_page()
    
    # 한글 폰트 설정 (폰트 파일이 없으면 깨질 수 있으므로 기본 영문으로 대체하거나 
    # 나중에 폰트 파일 업로드 로직을 추가해야 함. 여기서는 데모를 위해 기본 폰트 사용)
    # 실제 한글 출력을 위해서는 ttf 폰트 파일을 리포지토리에 올리고 경로를 지정해야 함.
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Learning Report", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10, style='B')
    pdf.cell(200, 10, txt="Original Content Summary:", ln=True)
    pdf.set_font("Arial", size=10)
    # multi_cell을 사용하여 줄바꿈 처리
    pdf.multi_cell(0, 10, txt=original_text[:500] + "...") # 너무 길면 자름
    pdf.ln(5)
    
    pdf.set_font("Arial", size=10, style='B')
    pdf.cell(200, 10, txt="AI Tutor Explanation:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=ai_explanation)
    
    # 임시 파일로 저장 후 바이트 리턴
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        pdf.output(tmp_file.name)
        return tmp_file.name

# --------------------------------------------------------------------------
# 3. 메인 UI 레이아웃
# --------------------------------------------------------------------------

st.title("📚 My Personal AI Learning Hub")
st.markdown("---")

# 화면을 좌우 6:4 비율로 분할
col1, col2 = st.columns([1, 2])

# [왼쪽] 수업 자료 영역
with col1:
    st.header("1. 수업 자료 업로드")
    uploaded_file = st.file_uploader("PDF, PPT(PDF변환), 동영상, 음성 파일 업로드", 
                                     type=['pdf', 'mp4', 'mp3'])

    extracted_text = "" # AI에게 보낼 텍스트

    if uploaded_file is not None:
        file_type = uploaded_file.type
        
        # PDF 처리
        if "pdf" in file_type:
            st.success("PDF 파일이 로드되었습니다.")
            # PDF 뷰어 (iframe 사용)
            base64_pdf = uploaded_file.getvalue()
            # PDF 내용을 텍스트로 추출 (AI 분석용)
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                extracted_text += page.extract_text()
            
            # PDF 화면 표시
            # 주의: 모바일 브라우저 등에서는 iframe PDF 뷰어가 제한될 수 있음
            import base64
            b64 = base64.b64encode(base64_pdf).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="600" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
            
        # 동영상/오디오 처리
        elif "video" in file_type:
            st.video(uploaded_file)
            st.info("동영상 자료는 내용 추출이 불가능하므로, 우측에 질문을 직접 입력해주세요.")
        elif "audio" in file_type:
            st.audio(uploaded_file)
            st.info("오디오 자료 재생 중...")

# [오른쪽] AI 설명 및 보충 자료 영역
with col2:
    st.header("2. AI 튜터 & 보충 학습")
    
    user_question = st.text_area("궁금한 점을 입력하거나, '설명해줘'라고 적으세요.", height=100)
    
    generate_btn = st.button("AI 설명 요청하기")
    
    if "ai_response" not in st.session_state:
        st.session_state.ai_response = ""

    if generate_btn:
        with st.spinner("제미나이가 문서를 분석 중입니다..."):
            if extracted_text:
                prompt = f"다음은 수업 자료의 내용입니다: {extracted_text[:3000]}... \n 이 내용을 바탕으로 사용자의 질문 '{user_question}'에 대해 쉽고 자세하게 설명해줘."
            else:
                prompt = f"사용자의 질문 '{user_question}'에 대해 학습 튜터로서 친절하게 설명해줘."
            
            try:
                response_text = get_gemini_response("", prompt)
                st.session_state.ai_response = response_text
                st.success("설명 생성 완료!")
            except Exception as e:
                st.error(f"오류 발생: {e}")

    # 결과 출력창
    st.markdown("### 🤖 Gemini의 설명")
    st.write(st.session_state.ai_response)
    
    st.markdown("---")
    st.header("3. 나만의 학습 자료 만들기")
    
    # PDF 다운로드 버튼
    if st.session_state.ai_response:
        if st.button("학습 리포트 PDF 생성"):
            pdf_path = create_pdf(extracted_text if extracted_text else "Video/Audio Material", st.session_state.ai_response)
            
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
                
            st.download_button(
                label="📥 PDF로 다운로드 받기",
                data=pdf_data,
                file_name="my_study_note.pdf",
                mime="application/pdf"
            )
            os.remove(pdf_path) # 임시 파일 삭제
