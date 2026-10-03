# UrjaMind: AI-Powered Energy Intelligence for Indian SMEs

## 1. Problem statement

Indian SMEs form a major part of the manufacturing base, yet they remain highly exposed to energy cost volatility. In many plants, energy cost can represent 15–30% of production cost, but plant managers lack clear visibility into where the energy is consumed, why it is increasing, and what practical action can reduce cost without affecting output.

The core challenges are:

1. Visibility gap: the plant has only a total electricity bill, not a machine-wise or section-wise view.
2. Diagnosis gap: they cannot tell whether increased cost comes from machine degradation, power factor issues, poor shift planning, or idle operation.
3. Action gap: they cannot schedule production around lower tariff periods or demand penalties without reducing throughput.
4. Proof gap: export buyers and compliance stakeholders increasingly ask for carbon data, but SMEs lack verified reporting standards and tools.

## 2. Why existing solutions are not enough

- IoT meter deployment is expensive and hard to scale across many SMEs.
- Most NILM research is focused on residential or high-resolution settings, not industrial SME environments.
- Deep learning systems often require large labeled datasets, which are not available in most plant settings.
- Tariff optimization work tends to be isolated to study-specific conditions rather than SME-ready plug-and-play tools.
- Carbon reporting remains fragmented and manual for most small units.

## 3. Proposed solution

UrjaMind is a hardware-free AI-driven energy intelligence platform for SMEs. It helps companies use their existing operational data—bills, interval data, production logs, and machine registers—to turn energy consumption into decisions.

The platform can:

- estimate machine or section-wise load from total plant data,
- diagnose waste and abnormal use patterns,
- recommend tariff-aware production schedules,
- estimate cost and emissions impact,
- generate carbon reports and plain-language insights for plant managers.

## 4. Zero-hardware data approach

UrjaMind is built around data that SMEs already have:

- electricity bill details such as total units, maximum demand, power factor, and TOD charges,
- DISCOM or utility interval data for 15–30 minute intervals,
- production logs showing output, product mix, and shift operations,
- equipment register with machine ratings and VFD information,
- public data for weather, tariff schedules, and grid emission factors.

### Data-tier model

The platform supports multiple data availability levels:

- Tier 1: monthly bill + production data
- Tier 2: 15–30 minute interval data
- Tier 3: higher-resolution or machine-level data when available

A confidence score is attached to outputs so users know how reliable a result is.

## 5. Platform architecture

### Layer 1: Data ingestion
- OCR for PDF and image bills
- CSV/Excel upload support
- WhatsApp bot input support
- schema validation and cleaning

### Layer 2: Plant digital twin
- synthetic plant model generated from equipment registers and operational assumptions
- simulates on/off duty cycles, startup spikes, idle loads, and VFD patterns
- provides labeled synthetic data where real plant labels are limited

### Layer 3: Disaggregation engine
- hybrid AI using transformer or CNN-style sequence models
- fallback statistical methods when data is sparse
- physical constraints to keep outputs realistic and consistent

### Layer 4: Baseline and anomaly detection
- expected energy forecasts using production, process, and weather variables
- waste detection for idle states, compressor leakage, furnace holding loads, and poor load patterns
- system identifies degradation before major downtime occurs

### Layer 5: Tariff-aware scheduler
- production planning around time-of-day tariffs and demand charges
- respects deadlines, machine availability, and process safety

### Layer 6: Carbon and copilot layer
- Scope 2 and Scope 1 calculations using electricity and fuel data
- GHG Protocol aligned reporting logic
- Hindi/Hinglish copilot summarizing evidence-backed insights for operators and managers

## 6. Technical methods

### AI and ML approach
- sequence models for load disaggregation
- Random Forest and statistical baselines for low-data settings
- synthetic digital-twin data for pretraining
- anomaly detection using residuals and drift monitoring
- optimization using Google OR-Tools CP-SAT constraint programming and sequential dispatch heuristics


### Why digital twins matter

Industrial plant data is often scarce and noisy, especially for SMEs. A digital twin allows the system to generate synthetic but realistic labeled data and to test operational scenarios such as motors, VFDs, and shift changes without waiting for real-world pilot data.

## 7. Example workflow

A foundry or textile unit uploads 30 days of interval data and production records.

UrjaMind identifies:

- a high base load during off-peak hours,
- idle compressor operation,
- production shifted to a high-tariff window,
- poor power factor causing demand or penalty issues,
- machine sections with abnormal energy intensity.

It then recommends:

- shifting certain jobs to lower-tariff hours,
- reducing idle machine operation,
- correcting capacitor bank configuration,
- tracking savings after intervention.

## 8. Impact and validation

The platform quantifies impact through a measurement-and-verification logic:
- baseline energy vs actual energy,
- production-adjusted savings,
- maximum demand reduction,
- rupee savings,
- carbon reduction.

The system reports model estimates and confidence levels rather than unverified savings claims.

### Estimated Prototype Savings Breakdown (Illustrative Case Study — Rajkot Foundry):
| Intervention Category | Specific Action | Monthly Impact | Method / Engine |
| :--- | :--- | :--- | :--- |
| **Tariff Scheduling** | Shift Furnace Melt #1 & #2 to off-peak / normal slots | **₹47,500 / mo** | Google OR-Tools CP-SAT (respects 250 kVA MD; 16.2% of base energy bill) |
| **Operational Waste** | Compressor night idle-draw shutoff (370 kWh unneeded run) | **₹8,400 / mo** | Physics residual & statistical baselining (illustrative) |
| **Asset Degradation** | Hydraulic Press #3 motor bearing maintenance | **₹2,800 / mo** | Specific energy creep tracking (+0.3%/day) |
| **Tariff Compliance** | APFC capacitor bank re-tuning (PF 0.87 → 0.95) | **₹1,200 / mo** | Measured DISCOM power factor penalty avoidance |
| **Total Combined Potential** | Combined illustrative interventions | **₹59,900 / mo** | *Model estimate (~20.2% total potential bill reduction; subject to factory pilot validation)* |

*Note: Scheduler shifts adjust production timing, whereas anomaly detection identifies unneeded idle leaks and mechanical wear. While addressing distinct mechanisms, combined totals are model projections to be validated on real factory sub-meters during Phase 2 pilot deployments.*

## 9. Business model


- Target sectors: foundries, textiles, ceramics, food processing, chemicals, brick kilns
- Channel partners: energy auditors, industrial associations, DISCOMs, OEMs
- Revenue model: monthly SaaS or shared-savings arrangement
- Early piloting: 10–20 plant clusters before scaling

## 10. Risk mitigation

- Sparse data: use tiered model and confidence-based outputs
- Lack of labeled industrial data: use digital twin synthetic generation
- LLM hallucination: restrict the copilot to tool-verified results and human-in-the-loop checks
- Trust barriers: present recommendation as a suggestion mode with savings proof

## 11. Closing summary

UrjaMind is a realistic, SME-friendly product concept that directly addresses a large and underserved market. It does not require expensive hardware installation, works with the data already available to factories, and converts energy data into operational decisions, financial savings, and carbon reporting readiness.

This makes it valuable not just as an AI concept, but as a practical platform for Indian industry transformation.
