import streamlit as st
import google.generativeai as genai
import os

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="AI Learning Platform",
    layout="wide"
)

st.title("Ultimate AI Learning Hub")
st.caption("PDF, PPT, 텍스트 기반 AI 학습 도우미")
st.markdown("---")

# -----------------------------
# Gemini API 설정
# -----------------------------
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    st.error("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
    st.stop()

genai.configure(api_key=API_KEY)

# -----------------------------
# 세션 상태 초기화
# -----------------------------
if "ai_response" not in st.session_state:
    st.session_state.ai_response = ""

# -----------------------------
# 레이아웃
# -----------------------------
col1, col2 = st.columns([1, 1])

# =============================
# 좌측: 학습 자료 입력
# =============================
with col1:
    st.subheader("학습 자료 입력")

    main_text = st.text_area(
        "메인 학습 자료",
        height=250,
        placeholder="여기에 학습할 내용을 붙여넣으세요"
    )

    supp_text = st.text_area(
        "보충 자료 (선택)",
        height=200,
        placeholder="추가 참고 자료가 있다면 입력하세요"
    )

# =============================
# 우측: AI 질문
# =============================
with col2:
    st.subheader("AI 튜터")

    user_question = st.text_area(
        "질문을 입력하세요",
        height=120,
        placeholder="이 개념을 쉽게 설명해줘"
    )

    if st.button("설명 요청", type="primary"):
        if not user_question:
            st.warning("질문을 입력하세요.")
        else:
            with st.spinner("AI가 분석 중입니다..."):
                try:
                    # Gemini 모델 (안정)
                    model = genai.GenerativeModel("gemini-pro")

                    prompt_parts = []
                    prompt_parts.append("당신은 친절하고 이해하기 쉽게 설명하는 AI 튜터입니다.")

                    if main_text.strip():
                        prompt_parts.append(
                            "다음은 메인 학습 자료입니다:\n" + main_text[:30000]
                        )

                    if supp_text.strip():
                        prompt_parts.append(
                            "다음은 보충 자료입니다:\n" + supp_text[:20000]
                        )

                    prompt_parts.append("질문:\n" + user_question)

                    prompt = "\n\n".join(prompt_parts)

                    response = model.generate_content(prompt)

                    # 응답 구조 호환 처리
                    if hasattr(response, "text") and response.text:
                        answer = response.text
                    else:
                        answer = response.candidates[0].content.parts[0].text

                    st.session_state.ai_response = answer

                except Exception as e:
                    st.error(f"에러 발생: {e}")
                    st.session_state.ai_response = ""

    if st.session_state.ai_response:
        st.markdown("### AI 답변")
        st.write(st.session_state.ai_response)
