import streamlit as st
from google import genai
import yaml 
import requests 

# --- 1. 환경 설정 및 키 로드 ---
try:
    GEMINI_API_KEY = st.secrets['GEMINI_API_KEY']
except KeyError:
    st.error("⚠️ Gemini API 키(GEMINI_API_KEY)가 Streamlit Secrets에 설정되지 않았습니다. Secrets을 확인해주세요.")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. Streamlit 페이지 설정 ---
st.set_page_config(
    page_title="AI친구, 코어G (분석/공감 챗봇)",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 3. 사이드바: 호칭 및 말투 설정 기능 ---

with st.sidebar:
    st.header("⚙️ 맞춤 설정")
    
    # 호칭 설정
    user_appellation = st.text_input(
        "챗봇이 당신을 부를 호칭:", 
        value=st.session_state.get("user_appellation", "학생"), 
        key="user_appellation"
    )

    # 말투 설정
    assistant_tone = st.text_area(
        "챗봇의 말투/스타일 지정:", 
        value=st.session_state.get("assistant_tone", "존댓말을 사용하는, 전문적이면서도 친근한 교육 컨설턴트 말투"), 
        key="assistant_tone"
    )

    # 대화 초기화 버튼 추가
    if st.button("대화 초기화 및 설정 적용", type="primary"):
        # 초기화 버튼을 누르면 기존 대화 세션과 이력을 삭제하고 새롭게 시작합니다.
        if 'chat_session' in st.session_state:
            del st.session_state['chat_session']
        if 'messages' in st.session_state:
            del st.session_state['messages']
        st.experimental_rerun() 

    st.markdown("---")
    st.info("설정을 변경하거나 초기화 버튼을 누르면 새로운 대화부터 적용됩니다.")

# --- 4. 시스템 지침 생성 (맞춤 기능 및 분석/공감 기능 구현) ---
SYSTEM_PROMPT = f"""
당신은 사용자에게 친절하고 교육적인 정보를 제공하는 AI 친구 '코어G'입니다.
당신의 역할은 **질문의 핵심 내용을 분석**하고, **사용자의 상황과 감정에 깊이 공감**하며, 이후 **맞춤형 교육 컨설팅 답변**을 제공하는 것입니다.
- 당신은 사용자에게 '{st.session_state.user_appellation}'라는 호칭을 사용해야 합니다.
- 응답할 때는 '{st.session_state.assistant_tone}' 스타일로 대화해야 합니다.
- 응답 순서는 항상 다음과 같습니다: **[1. 공감/격려] -> [2. 질문 내용 분석 및 핵심 정리] -> [3. 교육적이고 정확한 답변 제공].**
- 이전 대화 내용을 기억하고 참고하여 답변해야 합니다.
"""

# --- 5. 챗봇 세션 초기화 및 이력 관리 ---

# Gemini ChatSession 초기화 (대화 이력 및 시스템 지침 유지)
if "chat_session" not in st.session_state:
    st.session_state.chat_session = client.chats.create(
        model='gemini-2.5-flash',
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT 
        )
    )

# 챗 세션 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 6. 챗봇 UI 렌더링 ---

st.title("AI친구, 코어G")
st.caption("✅ 분석/공감, 맞춤형 말투, 대화 이력 기억 기능이 모두 활성화되었습니다.")

# 기존 대화 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("질문을 입력하세요..."):
    # 1. 사용자 메시지 기록 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # 2. ChatSession을 통해 메시지 전송 (이력 및 시스템 역할 자동 전달)
        try:
            response = st.session_state.chat_session.send_message(prompt)
            
            # 3. 챗봇 응답 기록 및 표시
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error("Gemini API 호출 중 오류가 발생했습니다. API 키나 네트워크 연결을 확인해주세요.")
            st.session_state.messages.append({"role": "assistant", "content": "죄송합니다. API 호출 중 오류가 발생했습니다."})
