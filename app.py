import os
import tempfile
import streamlit as st
from google import genai
from google.genai import types
import math
import json
from streamlit_mic_recorder import mic_recorder

# Set up page config
st.set_page_config(page_title="MechDiag AI", page_icon="⚙️", layout="centered", initial_sidebar_state="collapsed")

# Minimal CSS to hide footer and header and fix text visibility
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stApp > header {visibility: hidden;}
    
    /* Make the title centered and large */
    .gemini-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 500;
        margin-top: 15vh;
        margin-bottom: 2rem;
        letter-spacing: -0.5px;
        color: #ffffff !important;
    }
    
    /* Force ALL text to be bright white and readable */
    .stMarkdown, p, li, h1, h2, h3, h4, h5, h6, span {
        color: #ffffff !important;
    }
    
    /* Create a visible 'canvas' card for the AI results */
    .stChatMessage {
        background-color: #1e1f20 !important;
        border: 1px solid #444746 !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin-bottom: 15px !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3) !important;
    }
    
    /* Center container */
    .controls-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

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
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

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

# Only show the initial greeting if there are no messages
if not st.session_state.messages:
    st.markdown('<div class="gemini-title">What can I help with, Engineer?</div>', unsafe_allow_html=True)
else:
    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- CENTERED CONTROLS ABOVE CHAT INPUT ---
col1, col2, col3, col4, col5 = st.columns([1, 1, 3, 3, 1])

with col2:
    # The "+" button using st.popover to hide messy inputs
    with st.popover("➕"):
        st.markdown("**Attach Media**")
        uploaded_files = st.file_uploader("Files", accept_multiple_files=True, label_visibility="collapsed")
        st.markdown("**Camera**")
        camera_photo = st.camera_input("Camera", label_visibility="collapsed")

with col3:
    selected_model = st.selectbox(
        "Model",
        (
            "gemini-3.5-flash",
            "gemini-3-flash",
            "gemini-2.5-flash",
            "gemini-1.5-flash-latest",
        ),
        index=3,
        label_visibility="collapsed"
    )

with col4:
    # Key input
    api_key = st.text_input("API Key", type="password", placeholder="Enter API Key...", label_visibility="collapsed")
    if api_key:
        st.session_state.api_key = api_key

with col5:
    audio = mic_recorder(start_prompt="🎙️", stop_prompt="🛑", key="mic")

# --- RE-INIT AGENT IF SETTINGS CHANGE ---
if st.session_state.api_key and (st.session_state.chat_session is None or st.session_state.current_model != selected_model):
    try:
        client, chat = init_agent(st.session_state.api_key, selected_model)
        st.session_state.genai_client = client
        st.session_state.chat_session = chat
        st.session_state.current_model = selected_model
    except Exception as e:
        st.error(f"Error initializing agent: {e}")

# --- CHAT INPUT ---
prompt = st.chat_input("Ask MechDiag...")

# Execute when there's a prompt OR audio recording
if prompt or audio or camera_photo:
    if not st.session_state.api_key:
        st.error("Please enter an API Key in the field above first.")
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
                    st.rerun()
                except Exception as e:
                    st.error(f"Error connecting to AI: {e}")
