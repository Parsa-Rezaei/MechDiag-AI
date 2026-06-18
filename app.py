import os
import tempfile
import streamlit as st
from google import genai
from google.genai import types
import math
import json

# Set up page config
st.set_page_config(page_title="MechDiag AI", page_icon="⚙️", layout="wide")

# Custom CSS for modern minimal design
st.markdown("""
<style>
    /* Main background and text */
    .stApp {
        background-color: #f8f9fa;
        color: #212529;
    }
    
    /* Header minimalist */
    .css-10trblm {
        color: #2c3e50;
        font-weight: 600;
    }
    
    /* Chat bubbles */
    .stChatMessage {
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        background-color: white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
    }
    
    /* Inputs */
    .stTextInput>div>div>input, .stFileUploader>div>div>div>button {
        border-radius: 8px;
    }
    
    /* Hide some Streamlit default branding for minimal look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("⚙️ MechDiag AI")
st.markdown("<p style='color: #6c757d; font-size: 1.1rem; font-weight: 500;'>Modern Machinery Condition Monitoring Agent</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🔑 Setup")
    api_key = st.text_input("Enter your Gemini API Key", type="password")
    
    if not api_key:
        st.info("💡 **Welcome!** Please enter an API key above to start diagnosing.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.expander("📚 Help & Instructions"):
        st.markdown("1. Enter your API key.")
        st.markdown("2. Upload your machine data (PDFs, signals, images).")
        st.markdown("3. Ask the AI to diagnose the fault.")
        st.markdown("---")
        st.markdown("**Example:** 'Diagnose this pump based on the attached FFT report.'")

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
if "genai_client" not in st.session_state:
    st.session_state.genai_client = None

def init_agent(api_key):
    client = genai.Client(api_key=api_key)
    full_prompt = f"{system_prompt}\n\n---\n\n# DIAGNOSTIC RULES KNOWLEDGE BASE\n{diagnostic_rules}"
    
    # Create the chat session
    chat = client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=full_prompt,
            tools=[calculate_bearing_frequencies, classify_iso_severity, calculate_gear_mesh_frequency],
        )
    )
    return client, chat

if api_key and st.session_state.chat_session is None:
    try:
        client, chat = init_agent(api_key)
        st.session_state.genai_client = client
        st.session_state.chat_session = chat
    except Exception as e:
        st.sidebar.error(f"Error initializing agent: {e}")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# File Uploader & Chat Input Area
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")
col1, col2 = st.columns([1, 3])

with col1:
    uploaded_files = st.file_uploader("📎 Attach Files (PDF, Data, Images)", accept_multiple_files=True)

with col2:
    prompt = st.chat_input("Ask MechDiag to analyze...")

if prompt:
    if not api_key:
        st.error("Please enter an API Key in the sidebar first.")
    else:
        # Display user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            if uploaded_files:
                st.caption(f"📎 Attached {len(uploaded_files)} file(s)")

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Analyzing..."):
                try:
                    # Handle file uploads to Gemini using new SDK
                    gemini_parts = [prompt]
                    if uploaded_files:
                        for f in uploaded_files:
                            # Save to temp file
                            suffix = os.path.splitext(f.name)[1]
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                tmp.write(f.getbuffer())
                                tmp_path = tmp.name
                            
                            # Upload to Gemini
                            gem_file = st.session_state.genai_client.files.upload(file=tmp_path)
                            gemini_parts.append(gem_file)
                            
                            # Clean up
                            os.remove(tmp_path)
                    
                    # Send message (tools are handled automatically by the SDK!)
                    response = st.session_state.chat_session.send_message(gemini_parts)
                    final_text = response.text
                    message_placeholder.markdown(final_text)
                    st.session_state.messages.append({"role": "assistant", "content": final_text})
                except Exception as e:
                    st.error(f"Error connecting to AI: {e}. Please check your API key or file format.")
