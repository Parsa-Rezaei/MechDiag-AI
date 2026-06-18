import os
import streamlit as st
import google.generativeai as genai
import math
import json

# Set up page config
st.set_page_config(page_title="MechDiag AI", page_icon="⚙️", layout="wide")

st.title("⚙️ MechDiag AI")
st.subheader("Machinery Condition Monitoring Diagnostic Agent")

# Sidebar for API Key and instructions
with st.sidebar:
    st.markdown("### 🔑 Setup")
    api_key = st.text_input("Enter your Gemini API Key", type="password")
    if not api_key:
        st.warning("Please enter an API key to continue. You can get one for free from Google AI Studio.")
    
    st.markdown("---")
    st.markdown("### 📋 How to use")
    st.markdown("1. Enter your API key above.")
    st.markdown("2. Describe your machine's vibration data, symptoms, or upload FFT spectra.")
    st.markdown("3. The AI will guide you to the root cause using ISO standards and fault logic trees.")
    
    st.markdown("---")
    st.markdown("**Example Input:**")
    st.info("I have a centrifugal pump running at 2955 RPM. The overall vibration on the motor drive end horizontal is 7.8 mm/s RMS. The FFT shows a dominant peak at 49.25 Hz (1X RPM) at 7.2 mm/s. Phase horizontal is 45°, vertical is 138°.")

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
    return {
        "BPFO_hz": round(bpfo, 2), "BPFI_hz": round(bpfi, 2),
        "BSF_hz": round(bsf, 2), "FTF_hz": round(ftf, 2)
    }

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

# Chat input
if prompt := st.chat_input("Describe the vibration data here..."):
    if not api_key:
        st.error("Please enter an API Key in the sidebar first.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            with st.spinner("Analyzing..."):
                try:
                    response = st.session_state.chat_session.send_message(prompt)
                    
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
                    st.error(f"Error connecting to AI: {e}. Please check your API key.")
