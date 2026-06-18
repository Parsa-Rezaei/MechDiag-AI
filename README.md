# MechDiag AI — Machinery Condition Monitoring Diagnostic Agent

**Kaggle 5-Day AI Agents: Intensive Vibe Coding Course With Google — Capstone Project 2026**

---

## The Problem

Diagnosing mechanical faults in rotating machinery requires years of specialized training. A junior technician facing a vibrating pump motor must interpret FFT spectra, correlate phase readings, cross-reference bearing defect frequencies, and navigate complex logic trees to reach a root cause. Without this expertise, faults are misdiagnosed, maintenance budgets are wasted, and critical equipment fails unexpectedly.

The global predictive maintenance market exceeds $10 billion, yet most plants still rely on a small number of senior vibration specialists who are retiring faster than they can be replaced.

## The Solution: MechDiag AI

MechDiag AI is a **diagnostic reasoning agent** that operates as a virtual senior vibration analyst. Unlike traditional predictive maintenance dashboards that display data and leave interpretation to the user, MechDiag AI:

1. **Accepts multi-modal input** — FFT spectra, time waveforms, phase readings, thermal images, oil analysis reports, audio descriptions, equipment manuals, and machine parameters.
2. **Routes through a strict diagnostic logic tree** — based on established condition monitoring methodologies (ISO 13374, ISO 20816, Mobius Institute standards, Technical Associates of Charlotte fault matrices).
3. **Identifies what's missing** — instead of guessing when data is incomplete, the agent tells the user exactly what additional measurement to take and HOW to take it.
4. **Iterates toward 100% certainty** — each new piece of data narrows the possible faults until only one root cause remains.
5. **Verifies the fix** — after repair, the user uploads new readings and the agent confirms whether the fault is resolved.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    USER INPUT                       │
│  FFT · Phase · Thermal · Audio · Oil · Manuals · RPM │
└──────────────────────┬──────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────┐
│              MechDiag AI Agent                    │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │         System Prompt (Brain)               │   │
│  │  - Persona: Senior Vibration Analyst        │   │
│  │  - Rules: Never guess, always verify        │   │
│  │  - Output: Diagnostic Canvas format         │   │
│  └─────────────────────────────────────────────┘   │
│                       │                             │
│  ┌─────────────────────────────────────────────┐   │
│  │     Diagnostic Rules Knowledge Base (RAG)   │   │
│  │  - 10 fault branches (logic trees)          │   │
│  │  - ISO 20816-3 severity zones               │   │
│  │  - Bearing defect frequency formulas        │   │
│  │  - Gear mesh analysis rules                 │   │
│  │  - Electrical fault signatures              │   │
│  │  - Oil analysis cross-reference             │   │
│  └─────────────────────────────────────────────┘   │
│                       │                             │
│  ┌─────────────────────────────────────────────┐   │
│  │        Tools / Function Calls               │   │
│  │  - calculate_bearing_frequencies()          │   │
│  │  - classify_iso_severity()                  │   │
│  │  - query_diagnostic_literature()            │   │
│  │  - compare_baseline()                       │   │
│  └─────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────┐
│              DIAGNOSTIC CANVAS OUTPUT               │
│  Current Evidence · Possible Faults · Missing Data  │
│  Next Step · Severity · Repair Recommendation       │
└─────────────────────────────────────────────────────┘
```

## Key Differentiators

| Feature | Traditional CM Software | MechDiag AI |
|---------|------------------------|---------------|
| Input | Structured sensor data only | Multi-modal: text, images, documents, parameters |
| Diagnosis | Shows data, user interprets | Agent reasons through logic tree and explains |
| Incomplete data | Shows what it has, stops | Identifies gaps, tells user exactly what to measure next |
| Expertise level | Requires trained analyst | Accessible to junior technicians |
| Verification | Manual comparison | Post-repair data comparison with baseline |
| Memory | Stateless per session | Accumulates evidence across conversation |

## Project Files

```
MechDiag_Agent/
├── system_prompt.md          # Agent persona, logic tree, output format, ISO standards
├── diagnostic_rules.md       # Knowledge base: fault signatures, formulas, severity tables
├── sample_test_scenarios.json # 3 test scenarios (basic, ambiguous, multi-fault)
└── README.md                 # This file
```

## How to Use

### In Antigravity / Google AI Studio / Any Agent Framework

1. Load `system_prompt.md` as the system instruction for your LLM agent.
2. Load `diagnostic_rules.md` as the knowledge base context (or embed it into a RAG pipeline).
3. Start a conversation with one of the test scenarios from `sample_test_scenarios.json` to validate the agent's behavior.

### Example Interaction

**User:** "I have a centrifugal pump running at 2955 RPM. The overall vibration on the motor drive end horizontal is 7.8 mm/s RMS. The FFT shows a dominant peak at 49.25 Hz (1X RPM) at 7.2 mm/s, with very small 2X and 3X peaks. Phase horizontal is 45°, vertical is 138°. Axial vibration is only 1.2 mm/s."

**MechDiag AI:** Outputs a complete Diagnostic Canvas showing confirmed unbalance, Zone D severity, and recommends single-plane balance correction with post-repair verification.

**User:** "I have the same pump type but I only have horizontal FFT data. 1X is 4.1 mm/s and 2X is 3.8 mm/s. No phase data available."

**MechDiag AI:** Outputs Diagnostic Canvas with TWO possible faults (unbalance and misalignment), explains why it cannot confirm, and asks specifically for phase data across the coupling and axial vibration readings.

## Scientific Grounding

The diagnostic logic trees in this agent are grounded in:

- **ISO 20816-3:2022** — Vibration severity classification for industrial machines
- **ISO 13374** — Diagnostic architecture for condition monitoring systems
- **R.B. Randall, "Vibration-based Condition Monitoring"** (Wiley, 2011)
- **Mobius Institute** — Vibration analyst certification curriculum (CAT I–IV)
- **Technical Associates of Charlotte** — Illustrated Vibration Diagnostic Chart
- **SKF Bearing Diagnostics** — Defect frequency calculation methodology

## Limitations and Disclaimer

- MechDiag AI is a **decision-support tool**. It does not replace certified vibration analysts or reliability engineers for critical machinery decisions.
- The agent relies on the quality and accuracy of user-provided data. Incorrect RPM, wrong bearing models, or poor sensor mounting will degrade diagnostic accuracy.
- This capstone version uses the LLM's context window for knowledge retrieval. A production version would implement a proper vector database (FAISS/ChromaDB) for RAG over the full library of condition monitoring literature.

## Future Development Roadmap

- Real-time FFT signal upload and automatic peak detection
- Bearing catalog lookup API integration (SKF, FAG, NSK databases)
- Interactive Diagnostic Canvas visualization (web UI)
- Long-term machine memory database (Firebase/Supabase) for trending
- Audio analysis module for acoustic fault detection
- Integration with CMMS systems (SAP PM, Maximo, Fiix)

## Author

Mohammad Parsa Rezaei — PhD in Nonlinear Dynamics & Vibration Systems  
Lodz University of Technology, Poland

## License

MIT
