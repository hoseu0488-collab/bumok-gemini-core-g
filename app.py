import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import APIError
import base64
from gtts import gTTS # 텍스트-음성 변환
from io import BytesIO # 메모리에서 오디오 데이터 처리
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase # 마이크 입력

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
# 구문 오류를 발생시키던 모든 주석을 제거하여 오류를 확실히 방지합니다.
st.set_page_config(
    page_title="코어 G (음성 대화)", 
    layout="wide",
    description="당신의 마음을 공감하고 지식을 탐색하며 음성 대화가 가능한 AI 친구, 스피릿입니다. 💖"
) 

st.title("🤖 코어 G (스피릿)") 
st.subheader("💖 당신을 위해 존재하는 무료 AI 챗봇입니다.") 

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
        st.error(f"음성 출력(TTS) 오류: {e}")

# --- 음성 입력 클래스 (STT를 위한 마이크 스트림 처리) ---
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        pass

    def recv(self, frame):
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
    
    # 아바타 상태 관리 (
