import streamlit as st
import requests
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, RTCConfiguration
import numpy as np
from pydub import AudioSegment
import tempfile
import os
import threading
import av

# Configuration
st.set_page_config(page_title="Code&Clause Chat", page_icon="💼")
BASE_URL = "http://127.0.0.1:8000"

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "audio_frames" not in st.session_state:
    st.session_state.audio_frames = []
if "wav_bytes" not in st.session_state:
    st.session_state.wav_bytes = None
if "audio_captured" not in st.session_state:
    st.session_state.audio_captured = False

# Sidebar Navigation
st.sidebar.title("🔍 Navigation")
if st.session_state.get("logged_in"):
    page = st.sidebar.radio("Go to", ["🤖 Chat", "👤 Profile"], key="page_select")
else:
    page = st.sidebar.radio("Go to", ["🏠 Sign Up", "🔐 Login"], key="page_select")

# Auth Helpers (unchanged)
def signup():
    st.subheader("👤 Create an Account")
    st.text_input("First Name", key="signup_first")
    st.text_input("Last Name", key="signup_last")
    st.text_input("Email 📧", key="signup_email")
    st.text_input("Password 🔒", type="password", key="signup_pwd")
    st.selectbox("Role 🎭", ["staff", "admin"], key="signup_role")

    if st.button("Sign Up 🚀", key="signup_btn"):
        resp = requests.post(
            f"{BASE_URL}/auth/signup",
            json={
                "first_name": st.session_state.signup_first,
                "last_name": st.session_state.signup_last,
                "email": st.session_state.signup_email,
                "password": st.session_state.signup_pwd,
                "role": st.session_state.signup_role,
            },
        )
        if resp.status_code == 201:
            st.success("User created! Please log in.")
        else:
            st.error(resp.json().get("detail", "Signup failed."))

def login():
    st.subheader("🔐 Login")
    st.text_input("Email 📧", key="login_email")
    st.text_input("Password 🔒", type="password", key="login_pwd")

    if st.button("Login ✅", key="login_btn"):
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": st.session_state.login_email, "password": st.session_state.login_pwd},
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.token = data["access_token"]
            st.session_state.logged_in = True
            st.success("Logged in successfully!")
            st.rerun()
        else:
            st.error(resp.json().get("detail", "Login failed."))

def profile():
    st.subheader("👤 Profile")
    token = st.session_state.get("token")
    if not token:
        st.warning("Login to view profile.")
        return
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/auth/user/me", headers=headers)
    if resp.status_code == 200:
        user = resp.json()
        st.markdown(f"**Name:** {user['first_name']} {user['last_name']}")
        st.markdown(f"**Email:** {user['email']}")
        st.markdown(f"**Active:** {user['is_active']}")
        st.markdown(f"**Verified:** {user['is_verified']}")
    else:
        st.error("Failed to load profile.")

class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.frames = []
        self.lock = threading.Lock()
        
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        with self.lock:
            self.frames.append(frame.to_ndarray())
        return frame

def chat():
    st.subheader("🤖 Chat with Code&Clause")
    token = st.session_state.get("token")
    if not token:
        st.warning("Login to access chat.")
        return
    headers = {"Authorization": f"Bearer {token}"}

    # Display history
    hist_resp = requests.get(f"{BASE_URL}/chatbot/history/", headers=headers)
    if hist_resp.status_code == 200:
        for entry in hist_resp.json():
            st.markdown(f"**You:** {entry['user_input']}")
            st.markdown(f"**Bot:** {entry['response']} -- *{entry['timestamp']}*")
            st.markdown("---")

    # File upload
    uploaded = st.file_uploader("Upload file to send", type=None, key="file_upload")

    # Voice recording section
    st.markdown("### 🎤 Record Voice Message")
    
    webrtc_ctx = webrtc_streamer(
        key="audio-recorder",
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
        media_stream_constraints={"audio": True, "video": False},
        audio_processor_factory=AudioProcessor,
    )

    # Capture audio button
    if st.button("📸 Capture Audio"):
        if webrtc_ctx and webrtc_ctx.audio_processor:
            with webrtc_ctx.audio_processor.lock:
                audio_frames = webrtc_ctx.audio_processor.frames
                
                if audio_frames:
                    # Convert frames to audio
                    audio_data = np.concatenate(audio_frames, axis=0)
                    
                    # Create audio segment
                    audio_segment = AudioSegment(
                        audio_data.tobytes(),
                        sample_width=2,
                        frame_rate=48000,
                        channels=1
                    )
                    
                    # Save to bytes in session state
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        audio_segment.export(tmp.name, format="wav")
                        with open(tmp.name, "rb") as f:
                            st.session_state.wav_bytes = f.read()
                        os.unlink(tmp.name)
                    
                    st.session_state.audio_captured = True
                    st.success(f"Captured {len(audio_data)/48000:.2f}s of audio!")
                    webrtc_ctx.audio_processor.frames = []  # Clear frames
                else:
                    st.warning("No audio captured. Please speak and try again.")

    # Show captured audio and action buttons
    if st.session_state.audio_captured and st.session_state.wav_bytes:
        st.audio(st.session_state.wav_bytes, format="audio/wav")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Send Audio"):
                data = {"user_input": "<voice message>"}
                files = {"file": ("voice.wav", st.session_state.wav_bytes, "audio/wav")}
                
                with st.spinner("Sending audio..."):
                    resp = requests.post(
                        f"{BASE_URL}/chatbot/", 
                        data=data, 
                        headers=headers, 
                        files=files
                    )
                
                if resp.status_code == 200:
                    st.session_state.audio_captured = False
                    st.session_state.wav_bytes = None
                    st.rerun()  # Refresh after successful response
                else:
                    st.error(f"Error: {resp.text}")
                
        with col2:
            if st.button("Delete Audio"):
                st.session_state.audio_captured = False
                st.session_state.wav_bytes = None
                st.rerun()

    # Text input
    user_input = st.text_input("Type a message...", key="chat_input")

    # Send text message button
    if st.button("Send Message", key="send_msg") and user_input:
        data = {"user_input": user_input}
        files = None
        
        if uploaded:
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        
        with st.spinner("Sending message..."):
            resp = requests.post(
                f"{BASE_URL}/chatbot/", 
                data=data, 
                headers=headers, 
                files=files
            )
            
            if resp.status_code == 200:
                st.rerun()  # Refresh after successful response
            else:
                st.error(f"Error: {resp.text}")

# Main Render
if page == "🏠 Sign Up":
    signup()
elif page == "🔐 Login":
    login()
elif page == "👤 Profile":
    profile()
elif page == "🤖 Chat":
    chat()