import streamlit as st
from PyPDF2 import PdfReader
from pptx import Presentation
import openai
import os

# --------------------------------------------------
# 기본 설정
# --------------------------------------------------
st.set_page_config(page_title="나만의 AI 학습 사이트", layout="wide")
st.title("📚 나만의 영구적인 학습 사이트")
st.markdown("---")

# --------------------------------------------------
# OpenAI API 키 로딩 (안전)
# --------------------------------------------------
api_key = None

if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
elif os.getenv("OPENAI_API_KEY"):
    api_key = os.getenv("OPENAI_API_KEY")

if api_key is None:
    st.error("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
    st.stop()

openai.api_key = api_key

# --------------------------------------------------
# 파일 텍스트 추출 함수
# --------------------------------------------------
def get_pdf_text(file):
    text = ""
    try:
        reader = PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    except:
        return ""
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
        return ""
    return text

# --------------------------------------------------
# 화면 UI
# --------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.header("1. 자료 업로드")

    main_file = st.file_uploader(
        "메인 수업 자료 (PDF)",
        type=["pdf"]
    )

    supp_file = st.file_uploader(
        "보충 자료 (PDF / PPT)",
        type=["pdf", "pptx"]
    )

with col2:
    st.header("2. AI 튜터")

    question = st.text_area(
        "질문 또는 요청사항",
        "이 내용을 바탕으로 핵심 개념을 이해하기 쉽게 설명해줘."
    )

    generate_btn = st.button("🚀 설명 요청하기")

# --------------------------------------------------
# AI 응답 생성
# --------------------------------------------------
if generate_btn:
    if not main_file:
        st.warning("메인 자료를 먼저 업로드해주세요.")
        st.stop()

    with st.spinner("AI가 분석 중입니다..."):
        # 메인 자료
        main_text = get_pdf_text(main_file)

        # 보충 자료
        supp_text = ""
        if supp_file:
            if supp_file.name.endswith(".pdf"):
                supp_text = get_pdf_text(supp_file)
            elif supp_file.name.endswith(".pptx"):
                supp_text = get_pptx_text(supp_file)

        # 프롬프트 구성
        prompt = f"""
아래는 학습 자료이다.

[메인 자료]
{main_text[:6000]}

[보충 자료]
{supp_text[:4000]}

[요청]
{question}

대학생 수준에서 이해하기 쉽게,
구조적으로 정리해서 설명하라.
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "너는 친절한 AI 튜터이다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4
            )

            answer = response.choices[0].message.content
            st.success("분석 완료!")
            st.write(answer)

        except Exception as e:
            st.error(f"에러 발생: {e}")
