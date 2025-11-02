import streamlit as st
import os
from google import genai
from streamlit_oauth import OAuth2
import yaml
from yaml.loader import SafeLoader
import json # OAuth 응답을 처리하기 위해 추가

# --- 1. OAuth 설정 정보 (Streamlit Secrets에서 불러올 예정) ---
# 이 정보는 Secrets에 설정해야 합니다.
# -----------------------------------------------------------

# 임시로 설정 파일을 삭제하고 OAuth 객체를 초기화합니다.
# config.yaml 파일을 삭제했으므로, 이 부분을 주석 처리합니다.
# try:
#     with open('config.yaml') as file:
#         config = yaml.load(file, Loader=SafeLoader)
# except FileNotFoundError:
#     pass

# OAuth 설정 정의 (Streamlit Cloud Secrets에 저장해야 함!)
CLIENT_ID_KAKAO = os.environ.get("KAKAO_CLIENT_ID")
CLIENT_SECRET_KAKAO = os.environ.get("KAKAO_CLIENT_SECRET", "") # 카카오는 Secret이 필요 없을 수 있으나, 형식 유지
CLIENT_ID_GOOGLE = os.environ.get("GOOGLE_CLIENT_ID")
CLIENT_SECRET_GOOGLE = os.environ.get("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "https://share.streamlit.io/oauth_redirect" # 고정 리디렉션 URI

# --- 2. OAuth 객체 초기화 ---
oauth_providers = [
    {
        "provider": "google",
        "client_id": CLIENT_ID_GOOGLE,
        "client_secret": CLIENT_SECRET_GOOGLE,
        "authorize_url": "https://accounts.google.com/o/oauth2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": ["openid", "email", "profile"],
        "icon": "google",
        "pkce": True,
    },
    {
        "provider": "kakao",
        "client_id": CLIENT_ID_KAKAO,
        "client_secret": CLIENT_SECRET_KAKAO,
        "authorize_url": "https://kauth.kakao.com/oauth/authorize",
        "token_url": "https://kauth.kakao.com/oauth/token",
        "userinfo_url": "https://kapi.kakao.com/v2/user/me",
        "scope": ["profile_image", "account_email"],
        "icon": "chat-fill",
        "pkce": False,
        "custom_headers": {"Authorization": "Bearer TOKEN"}, # 카카오 토큰 헤더 설정
    },
]

# Client ID가 설정되어 있을 때만 OAuth 객체를 초기화합니다.
if CLIENT_ID_GOOGLE and CLIENT_ID_KAKAO:
    oauth = OAuth2(
        client_id="", # 이 라이브러리는 각 provider에 클라이언트 ID가 있으므로 빈 값으로 설정
        client_secret="",
        authorize_url="",
        token_url="",
        redirect_url=REDIRECT_URI,
        providers=oauth_providers,
    )
else:
    st.error("⚠️ OAuth 클라이언트 ID가 Streamlit Secrets에 설정되지 않았습니다. 외부 서비스 등록 후 Secrets을 확인해주세요.")
    st.stop()


# --- 3. 페이지 레이아웃 및 OAuth 로그인 처리 ---
st.title("✨ 모던 코어 G - 구독 서비스 (소셜 로그인)")

# 3-1. 소셜 로그인 시도
try:
    token = oauth.get_access_token(save_to_session=True)
except Exception as e:
    st.error(f"로그인 중 오류 발생: {e}")
    token = None


if token:
    # --- 로그인 성공: 토큰을 이용해 사용자 정보 가져오기 ---
    
    # 토큰을 세션에 저장
    st.session_state["token"] = token
    
    # [로그아웃 버튼 배치]
    with st.sidebar:
        if st.button("로그아웃"):
            st.session_state.clear()
            st.experimental_rerun()
            
        # 임시 사용자 정보 표시 (실제 서비스에서는 DB에서 가져와야 함)
        # 토큰을 사용하여 사용자 이름/이메일을 가져오는 로직이 추가되어야 합니다.
        st.subheader(f"환영합니다! 👋")
        
        # [구독 모델 뼈대 - 크레딧 표시 및 충전 버튼]
        st.markdown("---")
        st.info("💎 **현재 크레딧 잔액:** 100 크레딧 (구독 중)")
        st.button("크레딧/구독 충전 (결제 기능 추가 예정)", disabled=True) 
        st.markdown("---")

    # [기존 챗봇 코드]
    st.title("✨ 모던 코어 G (구독자 전용)")
    
    # Gemini API 키 확인
    if "GEMINI_API_KEY" not in os.environ:
        st.error("API 키(GEMINI_API_KEY)가 설정되지 않았습니다. Secrets을 확인해주세요.")
        st.stop()
        
    client = genai.Client()
    
    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "model", "parts": ["저는 모던 코어 G입니다. 무엇을 도와드릴까요?"]}]
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["parts"][0])
    
    if prompt := st.chat_input("메시지를 입력하세요."):
        st.session_state.messages.append({"role": "user", "parts": [prompt]})
        with st.chat_message("user"):
            st.markdown(prompt)
    
        with st.chat_message("model"):
            try:
                # [API 호출 및 사용량 기록 예정]
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[message["parts"][0] for message in st.session_state.messages],
                    system_instruction="당신은 모든 질문에 친절하고 유머러스하게 대답하는 최고의 AI 비서입니다.",
                )
                
                st.markdown(response.text)
                st.session_state.messages.append({"role": "model", "parts": [response.text]})
            except Exception as e:
                st.error(f"API 호출 중 오류가 발생했습니다: {e}")


else:
    # --- 4. 로그인 전: OAuth 버튼 표시 ---
    st.warning('월 구독 모델을 이용하시려면 소셜 계정으로 로그인해주세요.')
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("구글 로그인"):
            # 구글 로그인 페이지로 리디렉션
            oauth.authorize_url(provider="google") 
            
    with col2:
        if st.button("카카오 로그인"):
            # 카카오 로그인 페이지로 리디렉션
            oauth.authorize_url(provider="kakao")