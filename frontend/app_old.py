import streamlit as st
import requests
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, RTCConfiguration
import numpy as np
from pydub import AudioSegment
import tempfile
import os
import queue
import threading

# Configuration
st.set_page_config(page_title="Code&Clause Chat", page_icon="💼")
BASE_URL = "http://127.0.0.1:8000"

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "audio_frames" not in st.session_state:
    st.session_state.audio_frames = []
if "_reset_input" not in st.session_state:
    st.session_state._reset_input = False
if "_key_counter" not in st.session_state:
    st.session_state._key_counter = 0

# Sidebar Navigation
st.sidebar.title("🔍 Navigation")
if st.session_state.get("logged_in"):
    page = st.sidebar.radio("Go to", ["🤖 Chat", "👤 Profile"], key="page_select")
else:
    page = st.sidebar.radio("Go to", ["🏠 Sign Up", "🔐 Login"], key="page_select")

# Auth Helpers
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

# Audio Recorder Processor
class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_queue = queue.Queue()
        
    def recv(self, frame):
        self.audio_queue.put(frame.to_ndarray())
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

    # Voice recording
    st.markdown("### 🎤 Record Voice Message")
    
    webrtc_ctx = webrtc_streamer(
        key="audio-recorder",
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
        media_stream_constraints={"audio": True, "video": False},
        audio_processor_factory=AudioProcessor,
    )
    
    # Button to save recorded audio
    audio_captured = False
    audio_frames = []
    
    if webrtc_ctx.audio_processor:
        if st.button("📸 Capture Audio"):
            with st.spinner("Capturing audio..."):
                # Get audio frames from queue
                try:
                    while True:
                        audio_frames.append(webrtc_ctx.audio_processor.audio_queue.get(block=False))
                except queue.Empty:
                    pass
                
                if audio_frames:
                    st.session_state.audio_frames = audio_frames
                    audio_captured = True
                    st.success("Audio captured!")
                else:
                    st.warning("No audio captured. Try speaking louder.")

    # Text input - use the key and handle reset if needed
    if st.session_state.get("_reset_input", False):
        # Reset input by using a temporary key
        key_suffix = int(st.session_state.get("_key_counter", 0))
        st.session_state["_key_counter"] = key_suffix + 1
        input_key = f"chat_input_{key_suffix}"
        st.session_state["_reset_input"] = False
    else:
        input_key = "chat_input"
        
    user_input = st.text_input("Type a message...", key=input_key)

    if st.button("Send Message", key="send_msg"):
        data = {"user_input": user_input}
        files = None
        
        if uploaded is not None:
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        elif audio_captured or st.session_state.audio_frames:
            # Convert captured audio frames to WAV
            if not audio_captured:  # Use frames from session state
                audio_frames = st.session_state.audio_frames
                
            if audio_frames:
                # Concatenate audio frames and convert to WAV
                audio_data = np.concatenate(audio_frames, axis=0)
                wav = AudioSegment(
                    data=audio_data.tobytes(),
                    sample_width=2,
                    frame_rate=48000,
                    channels=1,
                )
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    wav.export(tmp.name, format='wav')
                    # Reopen the file for reading
                    with open(tmp.name, 'rb') as audio_file:
                        files = {"file": (os.path.basename(tmp.name), audio_file, 'audio/wav')}
                        
                        with st.spinner("Bot is thinking... 💡"):
                            resp = requests.post(
                                f"{BASE_URL}/chatbot/", data=data, headers=headers, files=files
                            )
                            if resp.status_code == 200:
                                st.markdown(f"**Bot:** {resp.json()['response']}")
                                # Set flag to reset input after successful submission
                                st.session_state["_reset_input"] = True
                                # Clear audio frames after sending
                                st.session_state.audio_frames = []
                            else:
                                st.error(f"Error contacting API: {resp.text}")
                
                # Clean up temp file
                os.unlink(tmp.name)
                return
        
        # If no audio or just text input
        with st.spinner("Bot is thinking... 💡"):
            resp = requests.post(
                f"{BASE_URL}/chatbot/", data=data, headers=headers, files=files
            )
            if resp.status_code == 200:
                st.markdown(f"**Bot:** {resp.json()['response']}")
                # Don't try to reset the input field directly
                # Instead, we'll set a flag to manage the state
                st.session_state["_reset_input"] = True
            else:
                st.error(f"Error contacting API: {resp.text}")
                
        # Reset the input after successful submission via session state flag
        if st.session_state.get("_reset_input", False):
            st.session_state["_reset_input"] = False

# Main Render
if page == "🏠 Sign Up":
    signup()
elif page == "🔐 Login":
    login()
elif page == "👤 Profile":
    profile()
elif page == "🤖 Chat":
    chat()