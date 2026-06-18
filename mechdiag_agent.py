"""
MechDiag AI — Machinery Condition Monitoring Diagnostic Agent
Kaggle 5-Day AI Agents Capstone Project 2026

Usage:
    1. Set your API key: export GOOGLE_API_KEY="your-key-here"
    2. Run: python mechdiag_agent.py
    3. Interact with the agent by describing your machine's vibration data

Security:
    - API key is loaded from environment variable ONLY
    - NEVER hardcode API keys in source code
    - For production: use Google Cloud Secret Manager or similar
"""

import os
import json
import math
import google.generativeai as genai


# ─────────────────────────────────────────────────────────────
# SECURITY: API Key from Environment Variable ONLY
# ─────────────────────────────────────────────────────────────
def get_api_key():
    """Load API key securely from environment variable."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "\n❌ GOOGLE_API_KEY environment variable not set.\n"
            "   Set it with: export GOOGLE_API_KEY='your-key-here'\n"
            "   Get a key at: https://aistudio.google.com/apikey\n"
        )
    return api_key


# ─────────────────────────────────────────────────────────────
# TOOL: Calculate Bearing Defect Frequencies
# ─────────────────────────────────────────────────────────────
def calculate_bearing_frequencies(
    n_balls: int,
    ball_diameter_mm: float,
    pitch_diameter_mm: float,
    contact_angle_deg: float,
    shaft_rpm: float,
) -> dict:
    """
    Calculate characteristic bearing defect frequencies.

    Args:
        n_balls: Number of rolling elements
        ball_diameter_mm: Rolling element diameter in mm
        pitch_diameter_mm: Pitch circle diameter in mm
        contact_angle_deg: Contact angle in degrees
        shaft_rpm: Shaft rotational speed in RPM

    Returns:
        Dictionary with BPFO, BPFI, BSF, FTF in Hz
    """
    theta = math.radians(contact_angle_deg)
    d_over_D = ball_diameter_mm / pitch_diameter_mm
    rpm_hz = shaft_rpm / 60.0

    bpfo = (n_balls / 2) * rpm_hz * (1 - d_over_D * math.cos(theta))
    bpfi = (n_balls / 2) * rpm_hz * (1 + d_over_D * math.cos(theta))
    bsf = (pitch_diameter_mm / (2 * ball_diameter_mm)) * rpm_hz * (
        1 - (d_over_D * math.cos(theta)) ** 2
    )
    ftf = (rpm_hz / 2) * (1 - d_over_D * math.cos(theta))

    return {
        "shaft_rpm": shaft_rpm,
        "shaft_frequency_hz": round(rpm_hz, 2),
        "BPFO_hz": round(bpfo, 2),
        "BPFI_hz": round(bpfi, 2),
        "BSF_hz": round(bsf, 2),
        "FTF_hz": round(ftf, 2),
        "harmonics": {
            "2X_BPFO": round(2 * bpfo, 2),
            "3X_BPFO": round(3 * bpfo, 2),
            "2X_BPFI": round(2 * bpfi, 2),
            "3X_BPFI": round(3 * bpfi, 2),
        },
    }


# ─────────────────────────────────────────────────────────────
# TOOL: Classify ISO 20816-3 Severity
# ─────────────────────────────────────────────────────────────
def classify_iso_severity(
    velocity_rms_mm_s: float,
    machine_group: int = 3,
) -> dict:
    """
    Classify vibration severity per ISO 20816-3.

    Args:
        velocity_rms_mm_s: Overall velocity in mm/s RMS
        machine_group: 1=Large rigid, 2=Medium rigid, 3=Pumps/motors, 4=Small

    Returns:
        Dictionary with zone classification and recommendation
    """
    # Zone boundaries by machine group [A/B boundary, B/C boundary, C/D boundary]
    boundaries = {
        1: [2.3, 4.5, 7.1],
        2: [1.4, 2.8, 4.5],
        3: [2.3, 4.5, 7.1],
        4: [0.71, 1.8, 4.5],
    }

    if machine_group not in boundaries:
        machine_group = 3  # default to pumps/motors

    b = boundaries[machine_group]
    v = velocity_rms_mm_s

    if v <= b[0]:
        zone = "A"
        status = "Excellent"
        action = "No action required. Machine in newly commissioned condition."
    elif v <= b[1]:
        zone = "B"
        status = "Acceptable"
        action = "Acceptable for long-term operation. Continue routine monitoring."
    elif v <= b[2]:
        zone = "C"
        status = "Warning"
        action = "Not suitable for long-term continuous operation. Plan maintenance intervention."
    else:
        zone = "D"
        status = "DANGER"
        action = "Dangerous vibration level. Risk of damage. Controlled shutdown recommended."

    return {
        "velocity_rms_mm_s": velocity_rms_mm_s,
        "machine_group": machine_group,
        "zone": zone,
        "status": status,
        "recommended_action": action,
        "zone_boundaries": {
            "A_upper": b[0],
            "B_upper": b[1],
            "C_upper": b[2],
            "D_lower": b[2],
        },
    }


# ─────────────────────────────────────────────────────────────
# TOOL: Calculate Gear Mesh Frequency
# ─────────────────────────────────────────────────────────────
def calculate_gear_mesh_frequency(
    n_teeth: int,
    shaft_rpm: float,
) -> dict:
    """
    Calculate gear mesh frequency and harmonics.

    Args:
        n_teeth: Number of teeth on the gear
        shaft_rpm: Rotational speed of the gear shaft in RPM

    Returns:
        Dictionary with GMF and harmonics
    """
    rpm_hz = shaft_rpm / 60.0
    gmf = n_teeth * rpm_hz

    return {
        "shaft_rpm": shaft_rpm,
        "shaft_frequency_hz": round(rpm_hz, 2),
        "n_teeth": n_teeth,
        "GMF_hz": round(gmf, 2),
        "2X_GMF_hz": round(2 * gmf, 2),
        "3X_GMF_hz": round(3 * gmf, 2),
        "expected_sidebands": {
            "GMF_minus_1X": round(gmf - rpm_hz, 2),
            "GMF_plus_1X": round(gmf + rpm_hz, 2),
        },
    }


# ─────────────────────────────────────────────────────────────
# LOAD SYSTEM PROMPT AND KNOWLEDGE BASE
# ─────────────────────────────────────────────────────────────
def load_file_content(filepath: str) -> str:
    """Load a text file's content. Returns empty string if not found."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"⚠️  File not found: {filepath}")
        return ""


# ─────────────────────────────────────────────────────────────
# BUILD THE AGENT
# ─────────────────────────────────────────────────────────────
def create_mechdiag_agent():
    """Initialize the MechDiag AI agent with tools and knowledge."""

    # Configure API
    api_key = get_api_key()
    genai.configure(api_key=api_key)

    # Load system prompt and knowledge base
    script_dir = os.path.dirname(os.path.abspath(__file__))
    system_prompt = load_file_content(os.path.join(script_dir, "system_prompt.md"))
    diagnostic_rules = load_file_content(os.path.join(script_dir, "diagnostic_rules.md"))

    # Combine into full system instruction
    full_system_instruction = (
        f"{system_prompt}\n\n"
        f"---\n\n"
        f"# DIAGNOSTIC RULES KNOWLEDGE BASE\n"
        f"The following is your complete reference library. Use it to ground "
        f"every diagnostic conclusion.\n\n"
        f"{diagnostic_rules}"
    )

    # Define tools for function calling
    tools = [
        genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(
                    name="calculate_bearing_frequencies",
                    description=(
                        "Calculate characteristic bearing defect frequencies "
                        "(BPFO, BPFI, BSF, FTF) from bearing geometry and shaft RPM. "
                        "Use when the user provides bearing specifications."
                    ),
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "n_balls": genai.protos.Schema(
                                type=genai.protos.Type.INTEGER,
                                description="Number of rolling elements",
                            ),
                            "ball_diameter_mm": genai.protos.Schema(
                                type=genai.protos.Type.NUMBER,
                                description="Rolling element diameter in mm",
                            ),
                            "pitch_diameter_mm": genai.protos.Schema(
                                type=genai.protos.Type.NUMBER,
                                description="Pitch circle diameter in mm",
                            ),
                            "contact_angle_deg": genai.protos.Schema(
                                type=genai.protos.Type.NUMBER,
                                description="Contact angle in degrees",
                            ),
                            "shaft_rpm": genai.protos.Schema(
                                type=genai.protos.Type.NUMBER,
                                description="Shaft RPM",
                            ),
                        },
                        required=[
                            "n_balls",
                            "ball_diameter_mm",
                            "pitch_diameter_mm",
                            "contact_angle_deg",
                            "shaft_rpm",
                        ],
                    ),
                ),
                genai.protos.FunctionDeclaration(
                    name="classify_iso_severity",
                    description=(
                        "Classify vibration severity per ISO 20816-3. "
                        "Returns zone (A/B/C/D), status, and recommended action."
                    ),
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "velocity_rms_mm_s": genai.protos.Schema(
                                type=genai.protos.Type.NUMBER,
                                description="Overall velocity in mm/s RMS",
                            ),
                            "machine_group": genai.protos.Schema(
                                type=genai.protos.Type.INTEGER,
                                description=(
                                    "Machine group: 1=Large rigid, 2=Medium rigid, "
                                    "3=Pumps/motors (default), 4=Small"
                                ),
                            ),
                        },
                        required=["velocity_rms_mm_s"],
                    ),
                ),
                genai.protos.FunctionDeclaration(
                    name="calculate_gear_mesh_frequency",
                    description=(
                        "Calculate gear mesh frequency (GMF) and harmonics "
                        "from tooth count and shaft RPM."
                    ),
                    parameters=genai.protos.Schema(
                        type=genai.protos.Type.OBJECT,
                        properties={
                            "n_teeth": genai.protos.Schema(
                                type=genai.protos.Type.INTEGER,
                                description="Number of teeth on the gear",
                            ),
                            "shaft_rpm": genai.protos.Schema(
                                type=genai.protos.Type.NUMBER,
                                description="Rotational speed of the gear shaft in RPM",
                            ),
                        },
                        required=["n_teeth", "shaft_rpm"],
                    ),
                ),
            ]
        )
    ]

    # Create the model with system instruction and tools
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=full_system_instruction,
        tools=tools,
    )

    return model


# ─────────────────────────────────────────────────────────────
# FUNCTION CALL DISPATCHER
# ─────────────────────────────────────────────────────────────
def handle_function_call(function_call):
    """Execute a function call from the model and return the result."""
    name = function_call.name
    args = dict(function_call.args)

    if name == "calculate_bearing_frequencies":
        result = calculate_bearing_frequencies(**args)
    elif name == "classify_iso_severity":
        result = classify_iso_severity(**args)
    elif name == "calculate_gear_mesh_frequency":
        result = calculate_gear_mesh_frequency(**args)
    else:
        result = {"error": f"Unknown function: {name}"}

    return result


# ─────────────────────────────────────────────────────────────
# MAIN CONVERSATION LOOP
# ─────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  MechDiag AI — Machinery Diagnostic Agent")
    print("  Kaggle AI Agents Capstone 2026")
    print("=" * 60)
    print()
    print("Describe your machine's vibration data, symptoms, or")
    print("upload FFT spectra. I will guide you to the root cause.")
    print()
    print("Type 'quit' or 'exit' to end the session.")
    print("Type 'test' to load a sample test scenario.")
    print("-" * 60)

    model = create_mechdiag_agent()
    chat = model.start_chat(enable_automatic_function_calling=False)

    while True:
        try:
            user_input = input("\n🔧 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nSession ended. Stay safe out there.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("\nSession ended. Stay safe out there.")
            break

        if user_input.lower() == "test":
            # Load test scenario 1 as a demo
            script_dir = os.path.dirname(os.path.abspath(__file__))
            test_file = os.path.join(script_dir, "sample_test_scenarios.json")
            try:
                with open(test_file, "r") as f:
                    scenarios = json.load(f)
                scenario = scenarios["test_scenarios"][0]
                user_input = (
                    f"Please diagnose this machine:\n"
                    f"{json.dumps(scenario['machine'], indent=2)}\n\n"
                    f"Vibration data:\n"
                    f"{json.dumps(scenario['vibration_data'], indent=2)}"
                )
                print(f"\n📋 Loaded test scenario: {scenario['scenario_name']}")
            except FileNotFoundError:
                print("⚠️  sample_test_scenarios.json not found.")
                continue

        # Send message to model
        try:
            response = chat.send_message(user_input)

            # Handle function calls if the model wants to use tools
            while response.candidates[0].content.parts:
                has_function_call = False
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call") and part.function_call.name:
                        has_function_call = True
                        fc = part.function_call
                        print(f"\n🔧 [Tool Call: {fc.name}]")
                        result = handle_function_call(fc)
                        print(f"   Result: {json.dumps(result, indent=2)}")

                        # Send function result back to model
                        response = chat.send_message(
                            genai.protos.Content(
                                parts=[
                                    genai.protos.Part(
                                        function_response=genai.protos.FunctionResponse(
                                            name=fc.name,
                                            response={"result": result},
                                        )
                                    )
                                ]
                            )
                        )
                        break  # re-check for more function calls

                if not has_function_call:
                    break

            # Print the final text response
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    print(f"\n🏥 MechDiag AI:\n{part.text}")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Please try rephrasing your input.")


if __name__ == "__main__":
    main()
