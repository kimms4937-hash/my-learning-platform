import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from fpdf import FPDF
import tempfile
import os
import time

# --------------------------------------------------------------------------
# 1. 기본 설정 및 Gemini 1.5 Pro (고성능 모델) 설정
# --------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="나만의 AI 학습 플랫폼 (Pro)")

try:
    # 3단계에서 입력한 API Key를 자동으로 가져옵니다.
    GENAI_API_KEY = st.secrets
    genai.configure(api_key=GENAI_API_KEY)
except Exception:
    st.error("🚨 API 키 오류: Streamlit Secrets에 'GENAI_API_KEY'가 설정되지 않았습니다.")
    st.info("Manage App -> Settings -> Secrets 메뉴에서 키를 입력해주세요.")

# --------------------------------------------------------------------------
# 2. 헬퍼 함수
# --------------------------------------------------------------------------

def get_pdf_text(pdf_file):
    """PDF 파일에서 텍스트를 추출하는 함수"""
    text = ""
    try:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        st.error(f"PDF 읽기 오류: {e}")
    return text

def create_pdf(original_text, ai_explanation):
    """결과물을 PDF로 저장하는 함수"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt="Learning Report (Gemini 1.5 Pro)", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=10, style='B')
    pdf.cell(200, 10, txt="Summary of Materials:", ln=True)
    pdf.set_font("Arial", size=10)
    # 한글 깨짐 방지를 위해 임시로 영어/숫자만 포함된 요약본 앞부분 사용 권장
    # (실제 한글 폰트 적용은 별도 폰트 파일 업로드 필요)
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

st.title("🧠 Pro AI Learning Hub (Gemini 1.5 Pro)")
st.caption("🚀 더 정확하고 똑똑한 Gemini 1.5 Pro 모델을 사용합니다. (속도는 조금 느릴 수 있습니다)")
st.markdown("---")

col1, col2 = st.columns([1, 1])

# [왼쪽] 자료 업로드 구역
with col1:
    st.subheader("📂 학습 자료 업로드")
    
    st.markdown("**1. 메인 수업 자료 (필수)**")
    main_file = st.file_uploader("수업 PDF (필수)", type=['pdf'], key="main")
    
    st.markdown("**2. 보충 자료 (선택)**")
    supp_file = st.file_uploader("보충 PDF (선택)", type=['pdf'], key="supp")

    # 텍스트 추출 변수 초기화
    main_text = ""
    supp_text = ""

    if main_file:
        main_text = get_pdf_text(main_file)
        st.success(f"✅ 메인 자료 로드 완료 ({len(main_text)}자)")

    if supp_file:
        supp_text = get_pdf_text(supp_file)
        st.success(f"✅ 보충 자료 로드 완료 ({len(supp_text)}자)")

# [오른쪽] AI 분석 구역
with col2:
    st.subheader("🤖 AI 튜터")
    
    user_question = st.text_area("질문 또는 요청사항 (예: 이 내용을 요약해줘)", height=100)
    
    # 버튼 클릭 로직
    if st.button("🚀 설명 요청하기 (High Quality)", type="primary"):
        # 1. 필수 조건 확인
        if not main_file and not user_question:
            st.warning("⚠️ 메인 자료를 업로드하거나 질문을 입력해주세요.")
        elif not st.secrets.get("GENAI_API_KEY"):
            st.error("⚠️ API 키가 설정되지 않았습니다.")
        else:
            # 2. 상태 표시 (Spinner 사용으로 '멈춤' 현상 방지)
            with st.status("🔍 AI가 자료를 분석하고 있습니다...", expanded=True) as status:
                try:
                    st.write("1. 자료 읽는 중...")
                    full_prompt = f"""
                    당신은 전문적인 개인 튜터입니다. 아래 자료를 깊이 있게 분석하여 사용자의 질문에 정확하게 답하세요.
                    
                    [메인 자료]:
                    {main_text[:20000]} 
                    
                    [보충 자료]:
                    {supp_text[:20000] if supp_text else "(없음)"}
                    
                    [사용자 질문]:
                    {user_question}
                    
                    핵심을 찌르는 명확하고 교육적인 설명을 제공하세요.
                    """
                    
                    st.write("2. Gemini 1.5 Pro 모델 연결 중...")
                    # 모델 변경: gemini-pro -> gemini-1.5-pro (더 똑똑함)
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    
                    st.write("3. 답변 생성 중... (잠시만 기다려주세요)")
                    # 스트리밍 응답 시작
                    response_container = st.empty()
                    full_response = ""
                    
                    response = model.generate_content(full_prompt, stream=True)
                    
                    for chunk in response:
                        if chunk.text:
                            full_response += chunk.text
                            response_container.markdown(full_response)
                    
                    # 결과 저장 (PDF 생성을 위해)
                    st.session_state.ai_response = full_response
                    status.update(label="✅ 분석 완료!", state="complete", expanded=False)
                    
                except Exception as e:
                    st.error(f"❌ 에러 발생: {e}")
                    status.update(label="❌ 처리 실패", state="error")

    # PDF 다운로드 버튼 (결과가 있을 때만 표시)
    if "ai_response" in st.session_state and st.session_state.ai_response:
        st.markdown("---")
        if st.button("📄 결과물 PDF로 저장"):
            pdf_path = create_pdf(main_text if main_text else "Question Only", st.session_state.ai_response)
            with open(pdf_path, "rb") as f:
                st.download_button("다운로드 시작", f, file_name="study_note_pro.pdf")
            os.remove(pdf_path)
