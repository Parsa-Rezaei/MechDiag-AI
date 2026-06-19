# Force Streamlit to reboot
import os
import tempfile
import streamlit as st
from google import genai
from google.genai import types
import math
import json
import base64
from streamlit_mic_recorder import speech_to_text

# Set up page config
st.set_page_config(page_title="MechDiag AI", page_icon="⚙️", layout="centered", initial_sidebar_state="expanded")

# --- BACKGROUND IMAGE WATERMARK ---
@st.cache_data
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_background_theme(light_file, dark_file):
    try:
        with open(light_file, "rb") as f:
            light_str = base64.b64encode(f.read()).decode()
        with open(dark_file, "rb") as f:
            dark_str = base64.b64encode(f.read()).decode()
            
        page_bg_img = f'''
        <style>
        .stApp::before {{
            content: "";
            background-image: url("data:image/png;base64,{light_str}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            opacity: 0.7;
            z-index: -1;
            pointer-events: none;
            mix-blend-mode: multiply;
        }}
        @media (prefers-color-scheme: dark) {{
            .stApp::before {{
                background-image: url("data:image/png;base64,{dark_str}");
                filter: none;
                mix-blend-mode: normal;
                opacity: 1.0;
            }}
        }}
        </style>
        '''
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except Exception:
        pass

set_background_theme('bg_pattern_light.png', 'bg_pattern_dark.png')

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
if "trigger_submit" not in st.session_state:
    st.session_state.trigger_submit = False
if "submitted_text" not in st.session_state:
    st.session_state.submitted_text = ""
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None
if "last_camera_id" not in st.session_state:
    st.session_state.last_camera_id = None
if "error_state" not in st.session_state:
    st.session_state.error_state = None
if "failed_text" not in st.session_state:
    st.session_state.failed_text = ""
if "last_processed_stt" not in st.session_state:
    st.session_state.last_processed_stt = None

def handle_text_submit():
    prompt = st.session_state.get("prompt_input", "")
    if isinstance(prompt, str) and prompt.strip():
        st.session_state.trigger_submit = True
        st.session_state.submitted_text = prompt.strip()
        st.session_state.prompt_input = ""
    else:
        st.session_state.trigger_submit = True
        st.session_state.submitted_text = "Please analyze the attached files."
        st.session_state.prompt_input = ""

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

if st.session_state.get("error_state"):
    with st.chat_message("assistant"):
        st.error(f"Error connecting to AI: {st.session_state.error_state}")
        if st.button("🔄 Try Again"):
            st.session_state.error_state = None
            st.session_state.trigger_submit = True
            st.session_state.submitted_text = st.session_state.failed_text
            st.rerun()

# --- SIDEBAR FOR API KEY ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.text_input("Gemini API Key", type="password", placeholder="Paste API Key here...", key="api_key")
    
    st.markdown("---")
    st.markdown("*Your key is secure and only used for this session.*")

# --- THE UNIFIED CHAT PILL ---
# This invisible anchor lets our CSS target the row directly below it
st.markdown('<div id="chat-bar-anchor"></div>', unsafe_allow_html=True)
col1, col2, col_send, col3, col5 = st.columns([1, 7, 1, 3, 1], gap="small")

with col1:
    with st.popover("➕"):
        st.markdown("**Attach Media**")
        uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True, label_visibility="collapsed")
        st.markdown("**Camera**")
        camera_photo = st.camera_input("Take Photo", label_visibility="collapsed")
        
with col2:
    new_stt = st.session_state.get("mic_stt_output")
    if new_stt and new_stt != st.session_state.get("last_processed_stt"):
        st.session_state.last_processed_stt = new_stt
        if isinstance(new_stt, str) and new_stt.strip():
            current = st.session_state.get("prompt_input", "")
            if isinstance(current, str) and current.strip():
                st.session_state.prompt_input = current + " " + new_stt
            else:
                st.session_state.prompt_input = new_stt
            
            
    prompt = st.text_input("Ask", placeholder="Ask MechDiag...", label_visibility="collapsed", key="prompt_input", on_change=handle_text_submit)

with col_send:
    st.button("↑", on_click=handle_text_submit, use_container_width=True)
    
with col3:
    selected_model = st.selectbox(
        "Model",
        ("gemini-3.5-flash", "gemini-3-flash", "gemini-2.5-flash"),
        index=0,
        label_visibility="collapsed"
    )
            
with col5:
    speech_to_text(start_prompt="🎙️", stop_prompt="🛑", key="mic_stt", language='en', use_container_width=True)


# --- RE-INIT AGENT IF SETTINGS CHANGE ---
if st.session_state.api_key and (st.session_state.chat_session is None or st.session_state.current_model != selected_model):
    try:
        client, chat = init_agent(st.session_state.api_key, selected_model)
        st.session_state.genai_client = client
        st.session_state.chat_session = chat
        st.session_state.current_model = selected_model
    except Exception as e:
        st.error(f"Error initializing agent: {e}")

# Check for new media that hasn't been processed yet
is_new_camera = False
if camera_photo is not None:
    cam_id = camera_photo.file_id
    if cam_id != st.session_state.last_camera_id:
        is_new_camera = True

# Execute when there's a prompt OR new camera
if st.session_state.trigger_submit or is_new_camera:
    st.session_state.error_state = None
    if not st.session_state.api_key:
        st.error("Please open the Settings sidebar on the left and enter your API Key first.")
        st.session_state.trigger_submit = False
    else:
        # Determine the user text
        user_text = "Please analyze the attached media."
        if st.session_state.trigger_submit:
            user_text = st.session_state.submitted_text
        elif is_new_camera:
            user_text = "I took a photo. Please analyze it."
            
        # Update last known states to prevent infinite loops
        if is_new_camera: st.session_state.last_camera_id = camera_photo.file_id
            
        # Save the media to session state so it survives the rerun!
        st.session_state.pending_camera = camera_photo if is_new_camera else None
        st.session_state.pending_files = uploaded_files if is_files_submit else None
            
        st.session_state.messages.append({"role": "user", "content": user_text})
        st.session_state.trigger_submit = False # Reset the submit flag
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
                
                # We pull the files from the session state to ensure they weren't wiped by the rerun
                # 1. Handle Text/CSV/PDF files
                if st.session_state.get('pending_files'):
                    for f in st.session_state.pending_files:
                        suffix = os.path.splitext(f.name)[1]
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                            tmp.write(f.getbuffer())
                            tmp_path = tmp.name
                        gem_file = st.session_state.genai_client.files.upload(file=tmp_path)
                        gemini_parts.append(gem_file)
                        os.remove(tmp_path)
                        
                # 2. Handle Camera Photo
                if st.session_state.get('pending_camera'):
                    cam_data = st.session_state.pending_camera
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                        tmp.write(cam_data.getbuffer())
                        tmp_path = tmp.name
                    gem_file = st.session_state.genai_client.files.upload(file=tmp_path)
                    gemini_parts.append(gem_file)
                    os.remove(tmp_path)
                
                # Send message
                response = st.session_state.chat_session.send_message(gemini_parts)
                final_text = response.text
                message_placeholder.markdown(final_text)
                st.session_state.messages.append({"role": "assistant", "content": final_text})
                
                # Clear pending media after successful send
                st.session_state.pending_camera = None
                st.session_state.pending_files = None
            except Exception as e:
                st.session_state.error_state = str(e)
                st.session_state.failed_text = user_text
                # Remove the failed message so they can try again
                st.session_state.messages.pop()
                st.rerun()
