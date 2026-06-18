# MechDiag AI — Diagnostic Rules Knowledge Base
# Source: Standard condition monitoring literature, ISO standards, and established fault matrices
# References: Mobius Institute curriculum, Technical Associates of Charlotte,
#             R.B. Randall "Vibration-based Condition Monitoring" (Wiley),
#             ISO 20816 series, ISO 13374 diagnostic architecture

---

## 1. VIBRATION SEVERITY STANDARDS

### ISO 20816-3:2022 — Vibration Severity for Industrial Machines
- Applies to machines with rated power above 15 kW
- Operating speeds: 120 RPM to 30,000 RPM
- Measurement: Overall velocity in mm/s RMS (broadband, typically 10 Hz – 1000 Hz)
- Zone A: Newly commissioned machines — excellent condition
- Zone B: Acceptable for unrestricted long-term operation
- Zone C: Not suitable for long-term operation — plan maintenance
- Zone D: Dangerous vibration levels — risk of damage, shutdown recommended
- Note: Zone boundaries depend on machine group (power, foundation, type)
- Note: These zones apply to BROADBAND (overall) vibration only; spectral narrowband analysis uses different evaluation criteria

### ISO 20816-1:2016 — General Principles
- Defines measurement locations: bearing housings, non-rotating structural parts
- Measurement directions: radial (vertical, horizontal) and axial
- Preferred sensors: accelerometers for high-frequency, velocity sensors for mid-frequency
- Displacement probes for shaft-relative measurements on journal bearings

---

## 2. UNBALANCE FAULT SIGNATURES

### Static Unbalance (Force Unbalance)
- Dominant 1X RPM in radial direction (H and V)
- V-H phase difference: approximately 0° or 180° (depending on sensor orientation)
- Axial 1X: low (less than 50% of highest radial)
- Phase: stable, repeatable
- In-phase across bearings on same rotor
- Fix: single-plane balance correction

### Couple Unbalance
- Dominant 1X RPM in radial direction
- 180° phase difference between bearings on same rotor (in same direction)
- Fix: two-plane balance correction

### Dynamic Unbalance (combination of static + couple)
- 1X RPM dominant radially
- Phase relationship between bearings varies
- Fix: two-plane balance correction (most common in practice)

### Key Differentiation Rule
- If 1X is high AND phase is UNSTABLE → NOT unbalance → check looseness
- If 1X is high AND doesn't respond to balancing → check resonance
- If 1X is high AND high axial → check misalignment

---

## 3. MISALIGNMENT FAULT SIGNATURES

### Angular Misalignment
- High 1X and 2X RPM in AXIAL direction
- 180° phase shift across coupling in AXIAL direction
- May also show 3X RPM
- High axial forces at coupling
- Often accompanied by coupling temperature increase

### Parallel (Offset) Misalignment
- High 2X RPM in RADIAL direction (sometimes exceeds 1X)
- 180° phase shift across coupling in RADIAL direction
- 1X RPM also elevated but 2X is typically dominant
- May produce both radial and axial vibration

### Key Differentiation Rule
- Angular → Primarily AXIAL, 1X + 2X
- Parallel → Primarily RADIAL, 2X dominant
- Real-world misalignment is usually a COMBINATION of both
- Critical test: 180° phase shift ACROSS the coupling is the strongest indicator
- Without cross-coupling phase data, misalignment cannot be confirmed with certainty

---

## 4. MECHANICAL LOOSENESS SIGNATURES

### Type A — Structural Looseness (Base/Foundation)
- 1X RPM dominant in radial
- Phase readings ERRATIC — differ by 30°+ between consecutive measurements
- Caused by: loose foundation bolts, cracked base plate, deteriorated grout
- Fix: tighten/replace foundation hardware, re-grout

### Type B — Component Looseness (Internal)
- Multiple harmonics: 1X, 2X, 3X ... up to 10X+ RPM
- May include sub-harmonics at 0.5X RPM
- "Haystack" pattern in spectrum
- Phase readings may or may not be stable
- Caused by: loose bearing in housing, loose rotor on shaft, excessive clearance
- Fix: inspect bearing fit, shaft tolerance, keyway condition

### Type C — Rotating Looseness (Rubbing)
- Multiple harmonics plus sub-harmonics
- Sub-synchronous activity (fractional harmonics: 1/2X, 1/3X, etc.)
- Truncated or clipped time waveform
- Caused by: seal rub, bearing rub, shaft contacting stationary parts
- Fix: inspect clearances, seals, bearing condition

---

## 5. ROLLING ELEMENT BEARING DEFECT SIGNATURES

### Stage 1 — Earliest Detection
- Ultrasonic range only (>20 kHz)
- No visible changes in standard FFT velocity spectrum
- Spike Energy, HFD, or acoustic emission detects changes
- Bearing is serviceable — monitor closely

### Stage 2 — Developing Defect
- Natural (resonant) frequencies of bearing components excited (1 kHz – 5 kHz range)
- Bearing defect frequencies may appear in envelope/demodulated spectrum
- Standard velocity FFT may still look normal
- Bearing may show slight temperature increase

### Stage 3 — Confirmed Defect
- Bearing defect frequencies (BPFI, BPFO, BSF) clearly visible in velocity spectrum
- Harmonics of defect frequencies present
- Sidebands around defect frequencies spaced at shaft speed (1X RPM)
- Envelope spectrum shows strong defect frequency components
- Increasing noise floor
- Plan replacement

### Stage 4 — End of Life
- Broadband noise floor significantly elevated
- Discrete peaks may actually decrease as defect becomes so large it's no longer periodic
- Overall vibration amplitude very high
- Audible noise, elevated temperature
- Random vibration characteristics
- REPLACE IMMEDIATELY — risk of catastrophic failure

### Defect Location Identification
- BPFO (outer race): Most common. Frequency does NOT modulate with shaft speed (stationary race). Clean, evenly-spaced impulses in time waveform.
- BPFI (inner race): Frequency IS modulated by shaft speed (rotating with shaft). Amplitude modulation at 1X RPM visible in time waveform.
- BSF (rolling element): Less common. May show 2X BSF due to defect contacting both races.
- FTF (cage/train): Low frequency. Rarely appears as distinct peak — usually modulates other frequencies.

---

## 6. GEAR FAULT SIGNATURES

### Normal Gear Mesh
- Gear Mesh Frequency (GMF) = Number of teeth × RPM
- GMF and low-amplitude harmonics (2X GMF, 3X GMF) are NORMAL
- Small, evenly-spaced sidebands at 1X RPM around GMF are NORMAL

### Gear Wear
- Increased amplitude at GMF and harmonics
- Sidebands increase in number and amplitude
- Sidebands spaced at RPM of the WORN gear
- Non-synchronous modulation possible with advanced wear

### Broken/Chipped Tooth
- Strong sidebands around GMF spaced at RPM of faulty gear shaft
- Natural frequency excitation (resonance) in high frequency range
- Time waveform shows periodic impulse once per revolution of faulty gear
- Impulse repeats at exactly 1X RPM of the damaged gear

### Gear Eccentricity / Backlash
- Sidebands around GMF at 1X RPM of eccentric gear
- GMF amplitude modulated at 1X RPM
- Phase measurement on gear housing can confirm

---

## 7. ELECTRICAL FAULT SIGNATURES (MOTORS)

### Stator Faults
- Dominant peak at 2X Line Frequency (2FL):
  - 50 Hz power system → 2FL = 100 Hz
  - 60 Hz power system → 2FL = 120 Hz
- 2FL peak DISAPPEARS INSTANTLY when power is cut
- Phase imbalance between motor phases
- Causes: winding shorts, unequal air gap (static eccentricity), power supply issues

### Rotor Faults (Broken Rotor Bars)
- 1X RPM peak with sidebands at pole-pass frequency
- Pole-pass frequency = slip frequency × number of poles
- Slip frequency = (synchronous speed - actual speed) / synchronous speed × line frequency
- Sidebands typically very close to 1X RPM (within ±5 Hz for typical 2-pole or 4-pole motors)
- Additional sidebands around 2FL at same spacing
- Distinguishing test: sidebands grow under LOAD

### Variable Frequency Drive (VFD) Effects
- VFDs create additional non-synchronous peaks
- Switching frequency and sidebands can appear in spectrum
- Need baseline with VFD to establish normal signature
- Some VFD-induced peaks are normal and not fault indicators

### Key Electrical vs Mechanical Differentiation
- CUT POWER TEST: If vibration peak disappears INSTANTLY → Electrical
- If vibration decays gradually (coasts down) → Mechanical
- This is the single most reliable test for electrical vs mechanical fault distinction

---

## 8. RESONANCE IDENTIFICATION

### Indicators
- Unusually high 1X RPM amplitude that does NOT respond to balance correction
- Phase shift of approximately 90° as RPM passes through natural frequency
- Amplitude spike when operating speed equals structural natural frequency
- Can create false high 1X readings that look like unbalance

### Confirmation Methods
- Bump test (impact test): Strike structure with instrumented hammer, measure response
- Coast-down/run-up test: Monitor amplitude vs RPM during speed change — resonance shows distinct peak
- Operating Deflection Shape (ODS) analysis

### Resolution
- Change operating speed to move away from natural frequency
- Add mass or stiffness to shift natural frequency
- Add damping to reduce amplification at resonance
- Structural modification (bracing, stiffening)

---

## 9. PUMP-SPECIFIC FAULTS

### Cavitation
- Broadband, random high-frequency noise (>1 kHz)
- No distinct discrete peaks (differentiates from bearing defects)
- Sounds like "gravel" or "marbles" rattling inside pump
- Caused by: insufficient NPSH, suction restrictions, high fluid temperature
- Check: suction pressure must exceed NPSHr (required) by margin
- Fix: increase suction head, reduce restrictions, lower fluid temperature

### Vane Pass Frequency
- Vane Pass Frequency (VPF) = Number of vanes × RPM
- Normal to see VPF in pump spectrum
- HIGH amplitude VPF indicates: wear ring clearance too large, impeller-to-volute gap issues
- Fix: check wear ring clearances, inspect impeller condition

### Recirculation
- Occurs at flows significantly below or above Best Efficiency Point (BEP)
- Low-frequency, broad energy, often sub-synchronous
- Flow noise, pressure fluctuations
- Fix: operate pump closer to BEP, install flow control

---

## 10. TRENDING AND BASELINE COMPARISON RULES

### Establishing Baselines
- Record baseline readings immediately after commissioning or successful repair
- Baseline should include: overall velocity, FFT spectrum, phase readings at key positions
- Minimum 3 measurement sets to confirm repeatability

### Alarm Threshold Guidelines
- Alert level: 2.5X baseline overall velocity value
- Danger level: 4X baseline overall velocity value OR entry into ISO Zone D
- Rate-of-change alarm: >50% increase in overall level within single monitoring interval

### Trending Rules
- Compare each new reading against the established baseline
- Track overall velocity trend over time
- Sudden spike: investigate immediately (acute failure, process upset)
- Gradual increase: schedule inspection at next opportunity
- Sudden decrease after sustained increase: possible Stage 4 bearing failure (loss of periodic impulse as defect becomes catastrophic)

---

## 11. OIL ANALYSIS CROSS-REFERENCE (MULTI-MODAL)

### Integration with Vibration Data
- Iron particles increasing + vibration at bearing defect frequencies → CONFIRM bearing wear
- Copper/bronze particles + vibration + temperature rise → bearing cage wear
- Silicon/dirt particles + bearing defect frequencies → contamination-induced bearing damage
- Normal oil analysis + high vibration → fault may be mechanical (misalignment, looseness) not wear-related yet

---

## 12. DATA QUALITY AND MEASUREMENT RULES

### Minimum Requirements for Reliable Analysis
- FFT resolution: at least 800 lines (preferably 1600 or 3200) for adequate frequency discrimination
- Frequency range (Fmax): at least 10X RPM for general analysis, higher for bearing analysis
- Averaging: minimum 4 averages, linear averaging for general, peak-hold for transients
- Measurement consistency: same location, same sensor, same mounting method each time
- Sensor mounting: stud mount preferred; magnet mount acceptable; hand-held probe NOT reliable for trending

### When to Question Data Quality
- If overall velocity seems unrealistically high (>20 mm/s on a small machine) → check sensor mounting
- If spectrum shows dominant peak at exactly 50/60 Hz → possible electrical pickup (ground loop)
- If all readings are extremely low (<0.2 mm/s) on a running machine → sensor may not be making proper contact
