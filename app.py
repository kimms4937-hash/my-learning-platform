import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import os

# ===============================
# 기본 설정
# ===============================
st.set_page_config(page_title="AI 학습 도우미", layout="wide")

# API 키
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# ===============================
# PDF 텍스트 추출 함수
# ===============================
def get_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# ===============================
# UI
# ===============================
st.title("📘 AI 학습 도우미")

uploaded_file = st.file_uploader("PDF 파일 업로드", type=["pdf"])
question = st.text_input("질문을 입력하세요")

# ===============================
# 실행 버튼
# ===============================
if st.button("답변 생성"):

    if uploaded_file is None or question.strip() == "":
        st.warning("PDF 파일과 질문을 모두 입력하세요.")
    else:
        with st.spinner("AI가 분석 중입니다..."):
            try:
                # PDF 읽기
                pdf_text = get_pdf_text(uploaded_file)

                # 프롬프트 구성
                prompt = f"""
아래는 학습 자료 내용이다.

{pdf_text[:30000]}

위 내용을 바탕으로 다음 질문에 답하라.

질문: {question}
"""

                # ✅ 여기 중요 — 이 모델만 사용
                model = genai.GenerativeModel("gemini-1.0-pro")

                response = model.generate_content(prompt)

                st.success("답변 생성 완료")
                st.write(response.text)

            except Exception as e:
                st.error(f"에러 발생: {e}")
