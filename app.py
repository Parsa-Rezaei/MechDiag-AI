import os
import tempfile
import streamlit as st
from google import genai
from google.genai import types
import math
import json
import base64
from streamlit_mic_recorder import mic_recorder

# Set up page config
st.set_page_config(page_title="MechDiag AI", page_icon="⚙️", layout="centered", initial_sidebar_state="expanded")

# --- BACKGROUND IMAGE WATERMARK ---
@st.cache_data
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_background(png_file):
    try:
        bin_str = get_base64_of_bin_file(png_file)
        page_bg_img = f'''
        <style>
        /* Add the image directly to the app background */
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }}
        /* Add a very dark overlay so the image becomes a subtle watermark, forcing dark mode aesthetic */
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background-color: rgba(19, 19, 20, 0.93);
            z-index: -1;
        }}
        </style>
        '''
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except Exception:
        pass

set_background('bg_pattern.png')

# Custom CSS to force the exact Gemini Dark Pill design
st.markdown("""
<style>
    /* Make the title centered and large */
    .gemini-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 500;
        margin-top: 5vh;
        margin-bottom: 2rem;
        letter-spacing: -0.5px;
        color: #ffffff !important;
    }

    /* Force ALL text to be bright white */
    .stMarkdown, p, li, h1, h2, h3, h4, h5, h6, span, label {
        color: #ffffff !important;
    }

    /* Make sidebar dark */
    [data-testid="stSidebar"] {
        background-color: #131314 !important;
        border-right: 1px solid #444746 !important;
    }
    
    /* Fix sidebar input box background and text visibility */
    [data-testid="stSidebar"] div[data-baseweb="input"] {
        background-color: #2b2c2f !important;
        border: 1px solid #444746 !important;
        border-radius: 6px !important;
    }
    
    /* Make everything inside the input box transparent with white text */
    [data-testid="stSidebar"] div[data-baseweb="input"] * {
        background-color: transparent !important;
        color: #ffffff !important;
    }
    
    /* Make the placeholder text light grey so it is readable */
    [data-testid="stSidebar"] input::placeholder {
        color: #b0b0b0 !important;
        opacity: 1 !important;
    }

    /* THE UNIFIED GEMINI PILL HACK */
    /* Target the exact row directly below the anchor */
    div:has(#chat-bar-anchor) + div.element-container > div[data-testid="stHorizontalBlock"] {
        background-color: #1e1f20 !important;
        border-radius: 50px !important;
        padding: 8px 20px !important;
        align-items: center !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.4) !important;
        border: 1px solid #444746 !important;
        margin-top: 30px !important;
        margin-bottom: 50px !important;
    }

    /* Strip background and borders from components inside the pill, and force text color to white */
    div:has(#chat-bar-anchor) + div.element-container > div[data-testid="stHorizontalBlock"] div[data-baseweb="input"] > div {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    div:has(#chat-bar-anchor) + div.element-container > div[data-testid="stHorizontalBlock"] input {
        color: #ffffff !important;
    }
    
    div:has(#chat-bar-anchor) + div.element-container > div[data-testid="stHorizontalBlock"] div[data-baseweb="select"] > div {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #ffffff !important;
    }
    
    div:has(#chat-bar-anchor) + div.element-container > div[data-testid="stHorizontalBlock"] div[data-baseweb="select"] span {
        color: #ffffff !important;
    }
    
    /* Style buttons inside the pill */
    div:has(#chat-bar-anchor) + div.element-container > div[data-testid="stHorizontalBlock"] button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #e3e3e3 !important;
        padding: 5px !important;
    }

    div:has(#chat-bar-anchor) + div.element-container > div[data-testid="stHorizontalBlock"] button:hover {
        background-color: rgba(255,255,255,0.1) !important;
        border-radius: 50% !important;
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

# Title
if not st.session_state.messages:
    st.markdown('<div class="gemini-title">What can I help with, Engineer?</div>', unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- SIDEBAR FOR API KEY ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    api_key_input = st.text_input("Gemini API Key", type="password", placeholder="Paste API Key here...")
    if api_key_input:
        st.session_state.api_key = api_key_input
    st.markdown("---")
    st.markdown("*Your key is secure and only used for this session.*")

# --- THE UNIFIED CHAT PILL ---
# This invisible anchor lets our CSS target the row directly below it
st.markdown('<div id="chat-bar-anchor"></div>', unsafe_allow_html=True)
col1, col2, col3, col5 = st.columns([1, 8, 3, 1], gap="small")

with col1:
    with st.popover("➕"):
        st.markdown("**Attach Media**")
        uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True, label_visibility="collapsed")
        st.markdown("**Camera**")
        camera_photo = st.camera_input("Take Photo", label_visibility="collapsed")
        
with col2:
    prompt = st.text_input("Ask", placeholder="Ask MechDiag...", label_visibility="collapsed")
    
with col3:
    selected_model = st.selectbox(
        "Model",
        ("gemini-3.5-flash", "gemini-3-flash", "gemini-2.5-flash", "gemini-1.5-flash-latest"),
        index=3,
        label_visibility="collapsed"
    )
            
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

# Execute when there's a prompt OR audio recording
if prompt or audio or camera_photo or (uploaded_files and st.button("Submit Attached Files")):
    if not st.session_state.api_key:
        st.error("Please click the '⋯' button in the chat bar and enter your API Key first.")
    else:
        # Determine the user text
        user_text = prompt if prompt else "Please analyze the attached media."
        if audio and not prompt:
            user_text = "I recorded an audio message. Please listen to it."
        if camera_photo and not prompt:
            user_text = "I took a photo. Please analyze it."
            
        st.session_state.messages.append({"role": "user", "content": user_text})
        st.rerun()

# --- TRIGGER EXECUTION ---
# This block handles the actual generation after a rerun so the user's message appears immediately
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    user_text = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        with st.spinner("Analyzing..."):
            try:
                gemini_parts = [user_text]
                
                # We pull the files from the current session state or variables if they exist
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
            except Exception as e:
                st.error(f"Error connecting to AI: {e}")
                # Remove the failed message so they can try again
                st.session_state.messages.pop()
