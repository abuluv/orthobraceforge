# Deliverable 6: Risk Matrix — Pediatric Medical Use

## Scope

This risk matrix covers the use of OrthoBraceForge for generating custom 3D-printed ankle-foot orthoses (AFOs) to treat idiopathic toe walking in pediatric patients (ages 2–12). Analysis follows ISO 14971:2019 (Medical devices — Application of risk management).

---

## Severity & Probability Definitions

### Severity Levels

| Level | Rating | Description |
|-------|--------|-------------|
| S1 | Negligible | No injury; cosmetic defect only |
| S2 | Minor | Temporary discomfort; skin redness; easily corrected |
| S3 | Moderate | Reversible injury requiring medical attention (pressure sore, skin breakdown) |
| S4 | Serious | Significant injury; falls resulting in fracture; prolonged treatment required |
| S5 | Critical | Permanent injury; catastrophic structural failure during gait |

### Probability Levels

| Level | Rating | Frequency |
|-------|--------|-----------|
| P1 | Improbable | <1 in 100,000 device uses |
| P2 | Remote | 1 in 10,000 to 1 in 100,000 |
| P3 | Occasional | 1 in 1,000 to 1 in 10,000 |
| P4 | Probable | 1 in 100 to 1 in 1,000 |
| P5 | Frequent | >1 in 100 device uses |

### Risk Acceptability Matrix

| | S1 | S2 | S3 | S4 | S5 |
|---|---|---|---|---|---|
| **P5** | Low | Medium | **HIGH** | **UNACCEPTABLE** | **UNACCEPTABLE** |
| **P4** | Low | Medium | **HIGH** | **HIGH** | **UNACCEPTABLE** |
| **P3** | Low | Low | Medium | **HIGH** | **UNACCEPTABLE** |
| **P2** | Low | Low | Low | Medium | **HIGH** |
| **P1** | Low | Low | Low | Low | Medium |

---

## Risk Register

### R-001: Incorrect Ankle Angle

| Field | Value |
|-------|-------|
| **Hazard** | AFO manufactured with ankle angle outside therapeutic range |
| **Cause** | Agent generates incorrect dorsiflexion/plantarflexion angle; parameter transcription error |
| **Harm** | Improper gait correction; potential for Achilles tendon strain or anterior tibial stress |
| **Severity** | S4 (Serious) |
| **Probability (pre-mitigation)** | P3 (Occasional) |
| **Risk (pre)** | **HIGH** |
| **Mitigations** | 1. Compliance RAG validates angle against clinical range (±15°) — blocks out-of-range values. 2. FEA node verifies biomechanical loading at specified angle. 3. **HUMAN REVIEW GATE: Clinician must verify ankle angle before approval.** 4. Dimensional tolerance check: ±1° per clinical spec. |
| **Probability (post-mitigation)** | P1 (Improbable) |
| **Risk (post)** | **Low** |
| **Human Oversight Checkpoint** | Phase 9: Mandatory clinician review of all angular parameters |

---

### R-002: Structural Failure During Gait

| Field | Value |
|-------|-------|
| **Hazard** | AFO fractures during walking, causing fall |
| **Cause** | Insufficient wall thickness; incorrect infill; material defect; build orientation error |
| **Harm** | Patient fall → fracture risk (pediatric bone fragility) |
| **Severity** | S5 (Critical) |
| **Probability (pre-mitigation)** | P3 (Occasional) |
| **Risk (pre)** | **UNACCEPTABLE** |
| **Mitigations** | 1. FEA stress analysis requires safety factor ≥ 3.0 (enforced). 2. AgenticAlloy agent evaluates need for Ti lattice reinforcement. 3. Minimum wall thickness enforced at 2.5mm (hard block in compliance_rag.py). 4. VLM critique checks for structural anomalies in rendered views. 5. **HUMAN REVIEW GATE: Clinician reviews FEA results and material selection.** 6. Print defect monitoring (LLM-3D-Print agent) detects layer adhesion failures. 7. Post-print physical load testing recommended in SOP. |
| **Probability (post-mitigation)** | P1 (Improbable) |
| **Risk (post)** | **Medium** (residual — requires physical testing) |
| **Human Oversight Checkpoints** | Phase 7: FEA review. Phase 8: Lattice decision. Phase 9: Final approval. Post-print: Physical test. |

---

### R-003: Pressure Injury / Skin Breakdown

| Field | Value |
|-------|-------|
| **Hazard** | AFO causes pressure sores on bony prominences (malleoli, fibular head) |
| **Cause** | Insufficient malleolar relief; trim lines too close to bone; rough internal surface |
| **Harm** | Skin breakdown, ulceration, infection risk in pediatric patient |
| **Severity** | S3 (Moderate) |
| **Probability (pre-mitigation)** | P4 (Probable) |
| **Risk (pre)** | **HIGH** |
| **Mitigations** | 1. Clinical spec enforces ≥3mm malleolar clearance (compliance_rag.py). 2. build123d template includes malleolar relief cutouts. 3. VLM critique specifically checks trim line proximity to bony landmarks. 4. Surface roughness spec: Ra < 12.5 µm enforced in material specs. 5. **HUMAN REVIEW GATE: Clinician verifies trim lines and relief areas.** 6. Post-fitting check required within 48 hours (documented in SOP). |
| **Probability (post-mitigation)** | P2 (Remote) |
| **Risk (post)** | **Low** |
| **Human Oversight Checkpoint** | Phase 9: Trim line and relief review. Post-fitting: 48-hour skin check. |

---

### R-004: Biocompatibility Reaction

| Field | Value |
|-------|-------|
| **Hazard** | Allergic or irritant reaction to 3D-printed material |
| **Cause** | Residual monomer leaching; support material residue; unapproved material selection |
| **Harm** | Contact dermatitis, allergic reaction (pediatric skin more sensitive) |
| **Severity** | S3 (Moderate) |
| **Probability (pre-mitigation)** | P3 (Occasional) |
| **Risk (pre)** | **Medium** |
| **Mitigations** | 1. Material database restricted to ISO 10993-validated materials only. 2. Compliance RAG blocks any material not in approved list. 3. Post-processing SOP requires solvent wash and UV curing. 4. **HUMAN REVIEW GATE: Material selection review.** 5. Patient/parent allergy screening in intake form. |
| **Probability (post-mitigation)** | P2 (Remote) |
| **Risk (post)** | **Low** |
| **Human Oversight Checkpoint** | Phase 2: Material validation. Phase 9: Material confirmation. |

---

### R-005: Incorrect Patient / Wrong Size

| Field | Value |
|-------|-------|
| **Hazard** | AFO manufactured for wrong patient or wrong foot dimensions |
| **Cause** | Data entry error; scan file mixup; bilateral L/R confusion |
| **Harm** | Ill-fitting device causing discomfort, pressure injuries, or ineffective treatment |
| **Severity** | S3 (Moderate) |
| **Probability (pre-mitigation)** | P4 (Probable) |
| **Risk (pre)** | **HIGH** |
| **Mitigations** | 1. Patient ID linked to all design records (SQLite FK constraint). 2. Scan file hash (SHA-256) recorded in audit trail — tamper-evident. 3. Anthropometric range check flags dimensions outside age-appropriate bounds. 4. Laterality explicitly tracked and displayed at every phase. 5. **HUMAN REVIEW GATE: Clinician verifies patient identity and dimensions.** 6. Audit PDF includes patient demographics for cross-check at fitting. |
| **Probability (post-mitigation)** | P2 (Remote) |
| **Risk (post)** | **Low** |
| **Human Oversight Checkpoint** | Phase 1: Identity verification. Phase 9: Dimensional review. Fitting: Physical match confirmation. |

---

### R-006: AI Agent Generates Unsafe Geometry

| Field | Value |
|-------|-------|
| **Hazard** | LLM/agent produces non-manifold, sharp-edged, or anatomically incorrect geometry |
| **Cause** | LLM hallucination; code generation error; self-correction loop exhaustion |
| **Harm** | Unprintable file (benign) to sharp internal edges causing lacerations (serious) |
| **Severity** | S4 (Serious) |
| **Probability (pre-mitigation)** | P4 (Probable) |
| **Risk (pre)** | **HIGH** |
| **Mitigations** | 1. Multi-agent fallback chain (build123d → OpenSCAD → Chat-To-STL). 2. Geometry validation: watertight check, dimension bounds, triangle count. 3. VLM render-critique catches visual anomalies. 4. Maximum iteration limit (10) prevents infinite loops. 5. **HUMAN REVIEW GATE: Clinician inspects 3D preview before approval.** 6. Software never silently generates — all outputs require explicit approval. |
| **Probability (post-mitigation)** | P2 (Remote) |
| **Risk (post)** | **Low** |
| **Human Oversight Checkpoint** | Phase 4: Auto-validation. Phase 6: VLM critique. Phase 9: Visual inspection in 3D preview. |

---

### R-007: Inadequate Growth Accommodation

| Field | Value |
|-------|-------|
| **Hazard** | AFO outgrown before replacement interval, causing restricted fit |
| **Cause** | Growth margin too small; replacement interval too long for patient's growth rate |
| **Harm** | Restrictive fit causing discomfort, potential circulatory issues |
| **Severity** | S3 (Moderate) |
| **Probability (pre-mitigation)** | P3 (Occasional) |
| **Risk (pre)** | **Medium** |
| **Mitigations** | 1. Age-based growth margins: 5mm for ages 2–6, 3mm for ages 7–12. 2. Replacement intervals: 6 months for <7yo, 12 months for ≥7yo. 3. Growth margin displayed prominently in design parameters. 4. **HUMAN REVIEW GATE: Clinician reviews growth accommodation.** 5. Audit report includes recommended follow-up date. |
| **Probability (post-mitigation)** | P2 (Remote) |
| **Risk (post)** | **Low** |
| **Human Oversight Checkpoint** | Phase 2: Growth parameter review. Phase 9: Accommodation confirmation. |

---

### R-008: Software Malfunction / Crash During Design

| Field | Value |
|-------|-------|
| **Hazard** | Application crash loses patient data or produces corrupted output |
| **Cause** | Unhandled exception; memory overflow; PyInstaller runtime error |
| **Harm** | Lost work (no patient harm if caught); corrupted STL if not caught |
| **Severity** | S2 (Minor) for data loss; S4 (Serious) for corrupted output used |
| **Probability (pre-mitigation)** | P3 (Occasional) |
| **Risk (pre)** | **Medium** to **HIGH** |
| **Mitigations** | 1. SQLite WAL mode prevents database corruption on crash. 2. STL hash verification in audit trail detects file corruption. 3. Pipeline state logged at each phase — resumable. 4. Try/catch wrapping on all agent calls with graceful error reporting. 5. **No output exported without completing full validation pipeline.** 6. **HUMAN REVIEW GATE: Cannot be reached without prior validation passes.** |
| **Probability (post-mitigation)** | P2 (Remote) |
| **Risk (post)** | **Low** |
| **Human Oversight Checkpoint** | Continuous: Error reporting in GUI trace log. Phase 9: Only reachable if all prior phases pass. |

---

### R-009: Print Defect Not Detected

| Field | Value |
|-------|-------|
| **Hazard** | Internal print defect (delamination, void) reduces structural integrity |
| **Cause** | Camera-based detection misses internal defect; printer malfunction |
| **Harm** | Latent structural weakness → failure during use (see R-002) |
| **Severity** | S4 (Serious) |
| **Probability (pre-mitigation)** | P3 (Occasional) |
| **Risk (pre)** | **HIGH** |
| **Mitigations** | 1. LLM-3D-Print agent monitors print in real-time (when camera available). 2. Critical defects trigger automatic print pause. 3. **Post-print physical inspection required (SOP).** 4. **Clinician must physically inspect device before patient fitting.** 5. Recommended: X-ray or CT scan of printed AFO for severe equinus cases. |
| **Probability (post-mitigation)** | P2 (Remote) |
| **Risk (post)** | **Medium** (residual — internal defects are inherently hard to detect) |
| **Human Oversight Checkpoint** | During print: Automated monitoring. Post-print: Physical inspection SOP. Pre-fitting: Clinician inspection. |

---

## Summary of Human Oversight Checkpoints

| # | Checkpoint | Pipeline Phase | Type | Bypassable? |
|---|-----------|----------------|------|-------------|
| 1 | Regulatory acknowledgment | Startup | Modal dialog | **No** |
| 2 | Patient identity verification | Phase 1 (Intake) | Clinician data entry | **No** |
| 3 | Compliance pre-check review | Phase 2 (Compliance) | Auto + display | No (blocks pipeline) |
| 4 | Dimensional range validation | Phase 3 (Parametric) | Automated | No (blocks pipeline) |
| 5 | FEA safety factor review | Phase 7 (FEA) | Auto + display | No (recorded in audit) |
| 6 | Lattice reinforcement decision | Phase 8 (Lattice) | Auto + display | No (recorded in audit) |
| 7 | **MANDATORY CLINICIAN APPROVAL** | **Phase 9 (Human Review)** | **Modal dialog — credentials required** | **NEVER** |
| 8 | Export file integrity | Phase 10 (Export) | SHA-256 hash | Automatic |
| 9 | Post-print physical inspection | Post-manufacturing | Manual SOP | Recommended |
| 10 | Patient fitting assessment | Clinical use | In-person | Required |
| 11 | 30-day follow-up | Post-delivery | Scheduled | Documented |

---

## Residual Risk Statement

After implementation of all mitigations, the overall residual risk of OrthoBraceForge for pediatric AFO generation is assessed as **ACCEPTABLE** provided that:

1. **All human oversight checkpoints are followed without exception.**
2. The software classification remains "INVESTIGATIONAL USE ONLY" until 510(k) clearance.
3. Every generated design undergoes mandatory clinician review (Phase 9).
4. Post-print physical inspection is performed per SOP.
5. Patient fitting includes 48-hour and 30-day follow-up assessments.
6. The software is never used as the sole basis for clinical decision-making.

**The most critical control is the MANDATORY HUMAN REVIEW GATE (Phase 9).** This gate cannot be disabled, bypassed, or automated. The `HUMAN_REVIEW_REQUIRED` flag in `config.py` is hardcoded to `True`, and the orchestrator logs a CRITICAL-level security violation if it is ever set to `False`.
