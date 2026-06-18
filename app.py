import os
import tempfile
import streamlit as st
from google import genai
from google.genai import types
import math
import json
from streamlit_mic_recorder import mic_recorder

# Set up page config
st.set_page_config(page_title="MechDiag AI", page_icon="⚙️", layout="wide")

# Custom CSS for Gemini Dark Mode look
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #131314;
        color: #e3e3e3;
        font-family: 'Google Sans', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Center aligning main title */
    .main-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 500;
        margin-top: 5vh;
        margin-bottom: 2rem;
        color: #e3e3e3;
        letter-spacing: -0.5px;
    }
    
    /* Chat bubbles */
    .stChatMessage {
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
        background-color: transparent;
    }
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #1e1f20;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #1e1f20;
        border-right: none;
    }
    
    /* Selectbox styling */
    div[data-baseweb="select"] > div {
        background-color: #1e1f20;
        color: white;
        border: 1px solid #444746;
        border-radius: 12px;
    }
    
    /* Input areas */
    .stChatInput {
        background-color: #1e1f20;
        border-radius: 24px;
        border: 1px solid #444746;
    }
    
    /* Hide some Streamlit default branding for minimal look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Sidebar for settings
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key = st.text_input("Enter your Gemini API Key", type="password")
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🧠 Model Selection")
    # Exact 2026 Models Dropdown
    selected_model = st.selectbox(
        "Choose AI Brain:",
        (
            "gemini-3.5-flash",
            "gemini-3-flash",
            "gemini-2.5-flash",
            "gemini-1.5-flash-latest",
        ),
        index=3  # Default to 1.5-flash as fallback
    )
    
    with st.expander("📚 Help & Instructions"):
        st.markdown("1. Enter your API key.")
        st.markdown("2. Select your preferred model.")
        st.markdown("3. Type, upload, record audio, or use the camera.")

# Load system prompt and rules
@st.cache_data
def load_knowledge():
    try:
        with open("system_prompt.md", "r", encoding="utf-8") as f:
            prompt = f.read()
        with open("diagnostic_rules.md", "r", encoding="utf-8") as f:
            rules = f.read()
        return prompt, rules
    except FileNotFoundError:
        return "", ""

system_prompt, diagnostic_rules = load_knowledge()

# Tools definitions
def calculate_bearing_frequencies(n_balls: int, ball_diameter_mm: float, pitch_diameter_mm: float, contact_angle_deg: float, shaft_rpm: float) -> dict:
    '''Calculate bearing defect frequencies (BPFO, BPFI, BSF, FTF).'''
    theta = math.radians(contact_angle_deg)
    d_over_D = ball_diameter_mm / pitch_diameter_mm
    rpm_hz = shaft_rpm / 60.0
    bpfo = (n_balls / 2) * rpm_hz * (1 - d_over_D * math.cos(theta))
    bpfi = (n_balls / 2) * rpm_hz * (1 + d_over_D * math.cos(theta))
    bsf = (pitch_diameter_mm / (2 * ball_diameter_mm)) * rpm_hz * (1 - (d_over_D * math.cos(theta)) ** 2)
    ftf = (rpm_hz / 2) * (1 - d_over_D * math.cos(theta))
    return {"BPFO_hz": round(bpfo, 2), "BPFI_hz": round(bpfi, 2), "BSF_hz": round(bsf, 2), "FTF_hz": round(ftf, 2)}

def classify_iso_severity(velocity_rms_mm_s: float, machine_group: int = 3) -> dict:
    '''Classify ISO severity zone (A, B, C, D) based on vibration velocity.'''
    boundaries = {1: [2.3, 4.5, 7.1], 2: [1.4, 2.8, 4.5], 3: [2.3, 4.5, 7.1], 4: [0.71, 1.8, 4.5]}
    b = boundaries.get(machine_group, boundaries[3])
    v = velocity_rms_mm_s
    if v <= b[0]: zone = "A"
    elif v <= b[1]: zone = "B"
    elif v <= b[2]: zone = "C"
    else: zone = "D"
    return {"zone": zone, "velocity_rms_mm_s": velocity_rms_mm_s}

def calculate_gear_mesh_frequency(n_teeth: int, shaft_rpm: float) -> dict:
    '''Calculate Gear Mesh Frequency (GMF) and 2X GMF.'''
    gmf = n_teeth * (shaft_rpm / 60.0)
    return {"GMF_hz": round(gmf, 2), "2X_GMF_hz": round(2 * gmf, 2)}

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "current_model" not in st.session_state:
    st.session_state.current_model = None

def init_agent(api_key, model_name):
    client = genai.Client(api_key=api_key)
    full_prompt = f"{system_prompt}\n\n---\n\n# DIAGNOSTIC RULES KNOWLEDGE BASE\n{diagnostic_rules}"
    
    # Create the chat session
    chat = client.chats.create(
        model=model_name,
        config=types.GenerateContentConfig(
            system_instruction=full_prompt,
            tools=[calculate_bearing_frequencies, classify_iso_severity, calculate_gear_mesh_frequency],
        )
    )
    return client, chat

# Re-init if the user changes the model or logs in
if api_key and (st.session_state.chat_session is None or st.session_state.current_model != selected_model):
    try:
        client, chat = init_agent(api_key, selected_model)
        st.session_state.genai_client = client
        st.session_state.chat_session = chat
        st.session_state.current_model = selected_model
    except Exception as e:
        st.sidebar.error(f"Error initializing agent: {e}")

# Main Layout
if not st.session_state.messages:
    # Show Gemini-like central greeting if empty
    st.markdown('<div class="main-title">What can I help with, Engineer?</div>', unsafe_allow_html=True)
else:
    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Input Controls Layout
st.markdown("<br>", unsafe_allow_html=True)
col_upload, col_mic, col_cam = st.columns([1, 1, 1])

with col_upload:
    uploaded_files = st.file_uploader("📎 Attach Data", accept_multiple_files=True)

with col_mic:
    # Streamlit Mic Recorder
    audio = mic_recorder(start_prompt="🎙️ Record Audio", stop_prompt="🛑 Stop Recording", key="mic")

with col_cam:
    # Streamlit Native Camera Input
    camera_photo = st.camera_input("📷 Take Photo")

prompt = st.chat_input("Ask MechDiag to analyze...")

# Execute when there's a prompt OR audio recording
if prompt or audio or camera_photo:
    if not api_key:
        st.error("Please enter an API Key in the sidebar first.")
    else:
        # Determine the user text
        user_text = prompt if prompt else "Please analyze the attached media."
        if audio and not prompt:
            user_text = "I recorded an audio message. Please listen to it."
        if camera_photo and not prompt:
            user_text = "I took a photo. Please analyze it."
            
        st.session_state.messages.append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)
            if uploaded_files: st.caption(f"📎 Attached {len(uploaded_files)} file(s)")
            if audio: st.caption("🎙️ Attached audio recording")
            if camera_photo: st.caption("📷 Attached camera photo")

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Analyzing..."):
                try:
                    gemini_parts = [user_text]
                    
                    # 1. Handle Text/CSV/PDF files
                    if uploaded_files:
                        for f in uploaded_files:
                            suffix = os.path.splitext(f.name)[1]
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                tmp.write(f.getbuffer())
                                tmp_path = tmp.name
                            gem_file = st.session_state.genai_client.files.upload(file=tmp_path)
                            gemini_parts.append(gem_file)
                            os.remove(tmp_path)
                            
                    # 2. Handle Audio Recording
                    if audio:
                        # audio dictionary contains bytes
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                            tmp.write(audio['bytes'])
                            tmp_path = tmp.name
                        gem_file = st.session_state.genai_client.files.upload(file=tmp_path)
                        gemini_parts.append(gem_file)
                        os.remove(tmp_path)
                        
                    # 3. Handle Camera Photo
                    if camera_photo:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                            tmp.write(camera_photo.getbuffer())
                            tmp_path = tmp.name
                        gem_file = st.session_state.genai_client.files.upload(file=tmp_path)
                        gemini_parts.append(gem_file)
                        os.remove(tmp_path)
                    
                    # Send message
                    response = st.session_state.chat_session.send_message(gemini_parts)
                    final_text = response.text
                    message_placeholder.markdown(final_text)
                    st.session_state.messages.append({"role": "assistant", "content": final_text})
                except Exception as e:
                    st.error(f"Error connecting to AI: {e}. Please check your API key, free-tier limits, or file format.")
