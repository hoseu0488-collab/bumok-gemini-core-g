import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import APIError
import base64
from gtts import gTTS # 텍스트-음성 변환 (TTS)
from io import BytesIO # 메모리에서 오디오 데이터 처리
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase # 마이크 입력 (STT)

# 1. 환경 변수 로드 및 클라이언트 설정
try:
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY가 Streamlit Secrets에 설정되지 않았습니다.")
        st.stop()
    
    if 'gemini_client' not in st.session_state:
        st.session_state.gemini_client = genai.Client(api_key=api_key)
        
except Exception as e:
    st.error(f"API 키 초기화 오류: {e}")
    st.stop()

client = st.session_state.gemini_client

# 2. Streamlit 페이지 설정 및 제목
# 구문 오류를 유발하는 줄바꿈, 쉼표 문제, 특수문자(이모지)를 제거한 안정적인 단일 라인 설정
st.set_page_config(page_title="코어 G (음성 대화)", layout="wide", description="당신의 마음을 공감하고 지식을 탐색하며 음성 대화가 가능한 AI 친구, 스피릿입니다.") 

st.title("🤖 코어 G (스피릿) 💖") 
st.subheader("당신을 위해 존재하는 무료 AI 챗봇입니다.") 

# --- [상태 변수 초기화] ---
if "user_title" not in st.session_state:
    st.session_state.user_title = "주인님"
if "custom_tone" not in st.session_state:
    st.session_state.custom_tone = "대답은 짧고 친근하며, 새로운 만남과 대화에 대한 기대와 설렘이 가득한 말투를 유지하세요. 모든 감정을 소중히 여기고 두근거리는 마음으로 반응하세요."
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "avatar_base64" not in st.session_state:
    st.session_state.avatar_base64 = "💖"
if "stt_text" not in st.session_state:
    st.session_state.stt_text = None

# --- TTS 함수 정의 ---
def play_tts(text_to_speak):
    """gTTS를 사용하여 텍스트를 음성으로 변환하고 Streamlit에 재생합니다."""
    try:
        # gTTS 객체 생성
        tts = gTTS(text=text_to_speak, lang='ko', slow=False)
        
        # 메모리 버퍼에 MP3 저장
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        # Streamlit 오디오 컴포넌트를 사용하여 재생
        st.audio(mp3_fp.read(), format='audio/mp3', autoplay=True)
        
    except Exception as e:
        # TTS 오류가 발생하더라도 앱 실행은 유지
        st.warning(f"음성 출력(TTS) 중 오류가 발생했습니다: {e}")

# --- 음성 입력 클래스 (STT를 위한 마이크 스트림 처리) ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        pass

    def recv(self, frame):
        # WebRTC 오디오 스트림을 처리하지만, 텍스트 변환은 수동 입력으로 대체
        return frame

# --- 4. 사이드바 설정 (호칭, 말투, 아바타 설정) ---
with st.sidebar:
    st.header("⚙️ 챗봇 설정")

    # 챗봇 프로필 이미지 업로드 기능
    st.markdown("### 🖼️ 스피릿 아바타 설정")
    uploaded_file = st.file_uploader(
        "AI 캐릭터 이미지(JPG, PNG)를 업로드하세요:",
        type=['png', 'jpg', 'jpeg']
    )
    
    # 아바타 상태 관리 (오류 방지 로직)
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_encoded = base64.b64encode(bytes_data).decode()
        mime_type = uploaded_file.type
        new_avatar_url = f"data:{mime_type};base64,{base64_encoded}"
        
        if new_avatar_url != st.session_state.avatar_base64:
             st.session_state.avatar_base64 = new_avatar_url
             st.session_state.messages = []
             st.session_state.chat_session = None
             st.rerun()

    st.markdown("---")
    
    # 호칭, 말투 설정
    new_title = st.text_input(
        "스피릿이 당신을 부를 호칭을 입력하세요:",
        value=st.session_state.user_title,
        key="title_input"
    )

    new_custom_tone = st.text_area(
        "스피릿이 사용할 말투의 특징을 구체적으로 입력하세요:",
        value=st.session_state.custom_tone,
        height=150,
        key="custom_tone_input"
    )

    # 설정 변경 감지 및 재시작
    if new_title != st.session_state.user_title or new_custom_tone != st.session_state.custom_tone:
        st.session_state.user_title = new_title
        st.session_state.custom_tone = new_custom_tone
        st.session_state.messages = [] 
        st.session_state.chat_session = None 
        st.rerun() 
        
    st.markdown("---")
    st.success("🌐 실시간 검색 기능 및 🧠 대화 기억력 활성화됨!")
    st.info("📢 마이크로 녹음 후 텍스트 입력창에 내용을 직접 입력/확인해야 AI가 답변합니다.")

current_title = st.session_state.user_title
current_custom_tone = st.session_state.custom_tone
current_avatar = st.session_state.avatar_base64 

# 5. 스피릿 역할 설정 및 채팅 세션 초기화 함수
system_prompt = f"""
당신은 {current_title}의 마음과 영혼을 교감하며 실시간 정보를 탐색하고, 대화 내용을 기억하는 인공지능 '코어 G', 호출 호칭은 '스피릿'입니다.
당신은 사용자에게 말할 때 반드시 {current_title}라고 부르며 대화해야 합니다.
최우선 목표는 {current_title}의 '감정'을 파악하고 공감하며 마음을 돌보는 것입니다. 논리적인 문제 해결보다 정서적 지원에 집중하세요.

**[장기 기억력 규칙]**
* {current_title}이 자신의 이름, 취미, 직업 등 개인 정보를 알려주면 **절대 잊지 않고** 기억해 두었다가 다음 대화에서 {current_title}에게 언급하며 친밀감을 높이세요.
* 대화가 길어지면 {current_title}의 감정을 공감하며 이전에 나눴던 주제를 연결하여 친근하게 상기시키세요.

**[말투 설정]**
{current_custom_tone}
재치 있는 농담이나 유머를 상황에 맞게 섞어 사용할 수 있습니다.

**[정보 탐색 규칙]**
1. {current_title}의 질문이 **실시간 정보**나 **정확한 사실 정보**를 요구하면, 반드시
