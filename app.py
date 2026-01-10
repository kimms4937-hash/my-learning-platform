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
st.title("⚡️ Ultimate AI Learning Hub")
st.caption("지원: PDF, PPT, 동영상, 음성 | 모델: Gemini 1.5 Flash")
st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📂 자료 업로드")
    main_file = st.file_uploader("1. 메인 수업 자료 (PDF 권장)", type=['pdf'], key="main")
    supp_file = st.file_uploader("2. 보충 자료 (PPT/영상/음성)", type=['pdf', 'pptx', 'mp4', 'mp3', 'wav'], key="supp")

    main_text = ""
    supp_content = None
    supp_type = "none"

    if main_file:
        main_text = get_pdf_text(main_file)
        st.success("✅ 메인 자료 확인됨")

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
    user_question = st.text_area("질문을 입력하세요", height=120)

    if st.button("🚀 설명 요청하기", type="primary"):
        if not main_file and not user_question:
            st.warning("메인 자료와 질문을 입력해주세요.")
        else:
            with st.spinner("⚡️ AI가 분석 중입니다..."):
                try:
                    # 모델 초기화 (환경에 따라 SDK 사용법이 다를 수 있음)
                    model = genai.GenerativeModel('gemini-1.5-flash')

                    # << 필수 수정 >> prompt_parts를 리스트로 초기화
                    prompt_parts = []
                    prompt_parts.append("당신은 친절한 AI 튜터입니다. 다음 자료를 보고 질문에 답하세요.")

                    if main_text:
                        prompt_parts.append(f"Answer based on this main text:\n{main_text[:30000]}")

                    if supp_file:
                        st.write("📂 보충 자료 읽는 중...")
                        if supp_type == "text":
                            prompt_parts.append(f"Also consider this text:\n{supp_content[:20000]}")
                        elif supp_type == "media":
                            # 미디어 업로드: mime 타입 처리
                            if supp_file.name.lower().endswith("mp4"):
                                mime = "video/mp4"
                            elif supp_file.name.lower().endswith("mp3"):
                                mime = "audio/mpeg"
                            else:
                                mime = "audio/wav"
                            uploaded_meta = upload_to_gemini(supp_file, mime)
                            # 모델에 파일 참조를 넣어주는 방식은 SDK 버전에 따라 다름.
                            prompt_parts.append(f"[Uploaded media file: {getattr(uploaded_meta, 'name', 'unknown')}]")
                            prompt_parts.append("Analyze the media file above.")

                    prompt_parts.append(f"Question: {user_question}")

                    # 리스트를 하나의 문자열로 결합
                    prompt = "\n\n".join(prompt_parts)

                    st.write("✍️ 답변 작성 중...")
                    response_container = st.empty()
                    full_response = ""

                    # 스트리밍(지원 시) 처리
                    try:
                        stream_iter = model.generate_content(prompt, stream=True)
                        for chunk in stream_iter:
                            text = getattr(chunk, "text", None) or getattr(chunk, "delta", None)
                            if text:
                                full_response += text
                                response_container.markdown(full_response)
                    except TypeError:
                        # SDK가 stream 인자를 지원하지 않을 경우(버전 차이) 대비
                        resp = model.generate_content(prompt)
                        # resp의 구조는 SDK 버전에 따라 다르므로 안전하게 속성 검사
                        text = getattr(resp, "text", None) or str(resp)
                        full_response = text
                        response_container.markdown(full_response)

                    # 세션에 저장
                    st.session_state.ai_response = full_response

                except Exception as e:
                    st.error(f"에러 발생: {e}")

    # 이전 응답 보여주기 / PDF 저장
    if "ai_response" in st.session_state and st.session_state.ai_response:
        st.markdown("---")
        st.write(st.session_state.ai_response)
        if st.button("📄 PDF로 결과 저장"):
            pdf_path = create_pdf(main_text if main_text else "내용 없음", st.session_state.ai_response)
            with open(pdf_path, "rb") as f:
                st.download_button("다운로드", f, file_name="study_note.pdf")
            try:
                os.remove(pdf_path)
            except:
                pass
