import os
import tempfile
import streamlit as st
import google.generativeai as genai
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
    theta = math.radians(contact_angle_deg)
    d_over_D = ball_diameter_mm / pitch_diameter_mm
    rpm_hz = shaft_rpm / 60.0
    bpfo = (n_balls / 2) * rpm_hz * (1 - d_over_D * math.cos(theta))
    bpfi = (n_balls / 2) * rpm_hz * (1 + d_over_D * math.cos(theta))
    bsf = (pitch_diameter_mm / (2 * ball_diameter_mm)) * rpm_hz * (1 - (d_over_D * math.cos(theta)) ** 2)
    ftf = (rpm_hz / 2) * (1 - d_over_D * math.cos(theta))
    return {"BPFO_hz": round(bpfo, 2), "BPFI_hz": round(bpfi, 2), "BSF_hz": round(bsf, 2), "FTF_hz": round(ftf, 2)}

def classify_iso_severity(velocity_rms_mm_s: float, machine_group: int = 3) -> dict:
    boundaries = {1: [2.3, 4.5, 7.1], 2: [1.4, 2.8, 4.5], 3: [2.3, 4.5, 7.1], 4: [0.71, 1.8, 4.5]}
    b = boundaries.get(machine_group, boundaries[3])
    v = velocity_rms_mm_s
    if v <= b[0]: zone = "A"
    elif v <= b[1]: zone = "B"
    elif v <= b[2]: zone = "C"
    else: zone = "D"
    return {"zone": zone, "velocity_rms_mm_s": velocity_rms_mm_s}

def calculate_gear_mesh_frequency(n_teeth: int, shaft_rpm: float) -> dict:
    gmf = n_teeth * (shaft_rpm / 60.0)
    return {"GMF_hz": round(gmf, 2), "2X_GMF_hz": round(2 * gmf, 2)}

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

def init_agent(api_key):
    genai.configure(api_key=api_key)
    full_prompt = f"{system_prompt}\n\n---\n\n# DIAGNOSTIC RULES KNOWLEDGE BASE\n{diagnostic_rules}"
    
    tools = [
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="calculate_bearing_frequencies",
                    description="Calculate bearing defect frequencies.",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "n_balls": genai.protos.Schema(type=genai.protos.Type.INTEGER),
                            "ball_diameter_mm": genai.protos.Schema(type=genai.protos.Type.NUMBER),
                            "pitch_diameter_mm": genai.protos.Schema(type=genai.protos.Type.NUMBER),
                            "contact_angle_deg": genai.protos.Schema(type=genai.protos.Type.NUMBER),
                            "shaft_rpm": genai.protos.Schema(type=genai.protos.Type.NUMBER),
                        },
                        required=["n_balls", "ball_diameter_mm", "pitch_diameter_mm", "contact_angle_deg", "shaft_rpm"]
                    )
                ),
                genai.protos.FunctionDeclaration(
                    name="classify_iso_severity",
                    description="Classify ISO severity.",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "velocity_rms_mm_s": genai.protos.Schema(type=genai.protos.Type.NUMBER),
                            "machine_group": genai.protos.Schema(type=genai.protos.Type.INTEGER),
                        },
                        required=["velocity_rms_mm_s"]
                    )
                ),
                genai.protos.FunctionDeclaration(
                    name="calculate_gear_mesh_frequency",
                    description="Calculate GMF.",
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "n_teeth": genai.protos.Schema(type=genai.protos.Type.INTEGER),
                            "shaft_rpm": genai.protos.Schema(type=genai.protos.Type.NUMBER),
                        },
                        required=["n_teeth", "shaft_rpm"]
                    )
                )
            ]
        )
    ]
    model = genai.GenerativeModel(model_name="gemini-2.0-flash", system_instruction=full_prompt, tools=tools)
    return model.start_chat(enable_automatic_function_calling=False)

def handle_function_call(fc):
    name = fc.name
    args = dict(fc.args)
    if name == "calculate_bearing_frequencies": return calculate_bearing_frequencies(**args)
    elif name == "classify_iso_severity": return classify_iso_severity(**args)
    elif name == "calculate_gear_mesh_frequency": return calculate_gear_mesh_frequency(**args)
    return {"error": "Unknown function"}

if api_key and st.session_state.chat_session is None:
    try:
        st.session_state.chat_session = init_agent(api_key)
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
                    # Handle file uploads to Gemini
                    gemini_parts = [prompt]
                    if uploaded_files:
                        for f in uploaded_files:
                            # Save to temp file
                            suffix = os.path.splitext(f.name)[1]
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                                tmp.write(f.getbuffer())
                                tmp_path = tmp.name
                            
                            # Upload to Gemini
                            gem_file = genai.upload_file(tmp_path)
                            gemini_parts.append(gem_file)
                            
                            # Clean up
                            os.remove(tmp_path)
                    
                    # Send message
                    response = st.session_state.chat_session.send_message(gemini_parts)
                    
                    # Handle tools
                    while response.candidates and response.candidates[0].content.parts:
                        has_fc = False
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, "function_call") and part.function_call.name:
                                has_fc = True
                                fc = part.function_call
                                result = handle_function_call(fc)
                                response = st.session_state.chat_session.send_message(
                                    genai.protos.Content(parts=[
                                        genai.protos.Part(function_response=genai.protos.FunctionResponse(
                                            name=fc.name, response={"result": result}
                                        ))
                                    ])
                                )
                                break
                        if not has_fc: break
                    
                    if response.candidates and response.candidates[0].content.parts:
                        final_text = response.candidates[0].content.parts[0].text
                        message_placeholder.markdown(final_text)
                        st.session_state.messages.append({"role": "assistant", "content": final_text})
                except Exception as e:
                    st.error(f"Error connecting to AI: {e}. Please check your API key or file format.")
