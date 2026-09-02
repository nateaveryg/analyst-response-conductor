# Gartner Magic Quadrant for AI Coding Agents (2026)
## Consolidated Evaluation & Demonstration Orchestration Report (Dual-Input)

**Date:** July 14, 2026  
**Input Sources Parsed (`rficonductorv2`):**
1. **Welcome Packet & Inclusion Criteria:** `Inclusion Criteria_Magic Quadrant and Critical Capabilities for AI Coding Agents 2026.docx` (`1FOeqtkipfGAAIv-FEiRHRa3-rE4RM-nD`)
2. **Vendor Demonstration Guidelines:** `Vendor Demonstration Guidelines for MQ-CC DevSecOps Platforms 2026.pdf` (`1cXYqEen7D0nACmME8XAkvCfbZrpP0pSn`)

**Key Target Deadlines:**
* **Stage 1 (Attestation & RFI Questionnaire):** February 27, 2026 (5:00 PM EST)
* **Stage 2 (Product Demo & TOC Portal Upload):** March 10, 2026 (11:59 PM PT)
* **General Availability (GA) Cutoff Date:** March 2, 2026  

---

## 1. Executive Summary & Combined Market Requirements

By executing `rficonductorv2` with **both** the Welcome Packet and the Vendor Demonstration Guidelines as simultaneous inputs, the orchestration engine synthesizes financial eligibility rules with multimedia production constraints into a unified execution plan.

Gartner defines **AI Coding Agents** as:
> *"Autonomous or semiautonomous software engineering solutions that perceive context, translate human intent into multistep plans, and execute and verify those steps across code, tests and related engineering artifacts."*

### Extracted Consolidated Rules (`InclusionAnalyzer` & `TimelineEngine`)
* **General Availability (GA) Cutoff (`2026-03-02`):** All mandatory agent capabilities must be generally available and listed on a public price sheet by March 2, 2026. No Beta, Preview, or Limited Access features qualify for inclusion.
* **Financial & Scale Floors (CY 2025 / as of Dec 31, 2025):**
  * **Option A:** $\ge 500$ paying enterprise customer organizations (logos), OR
  * **Option B:** $\ge \$25\text{M}$ recognized GAAP revenue AND either $\ge 40\%$ YoY revenue growth (CAGR) or $\ge 50$ net-new paying logos.
* **Multi-Product Evaluation Mandate:** *"For situations where multiple products are under evaluation, please upload a demo for each product."* `rficonductorv2` automatically triggers separate demo production tracks for every qualifying SKU in `eligible_products`.
* **Demonstration Video & Portal Constraints:**
  * **Hard Duration Cap:** Maximum **60 minutes per video** (Gartner evaluators stop watching at exactly 01:00:00).
  * **Technical Specs:** $720\text{p}+$ resolution in `.mp4` format; maximum **$4\text{GB}$ per file**; up to **10 files** total allowed on the portal.
  * **Portal Governance:** Only designated **Administrators** can upload and submit files via the Gartner Provider Information Portal.
  * **Table of Contents (TOC) Mandate:** Must submit a separate table of contents file indicating exact `[mm:ss]` timecodes for each topic, Use Case, and Critical Capability.

---

## 2. Multi-Product Portfolio Eligibility Matrix

Evaluating Google's portfolio under the dual-input rules confirms that **multiple qualifying offerings can be submitted**. The engine evaluates individual SKUs against GA and scale floors while enabling portfolio aggregation where permitted by analyst definitions.

| Offering Name | GA Date | CY 2025 Revenue | Growth / CAGR | Enterprise Logos | Rule Violations Identified | Multi-Product Recommendation |
| :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| **Gemini Code Assist Enterprise (Standard GA)** | `2024-11-15` | $\$35,000,000$ | $65.0\%$ | $620$ | *None* (Meets & exceeds all floors) | ✅ **Qualifies as Primary Flagship SKU** (`Proceed_With_Participation`) |
| **Gemini Code Assist Agent Mode (Preview)** | `2026-04-15` | $\$8,500,000$ | $120.0\%$ | $410$ | ❌ **GA Cutoff Violation:** GA date (`2026-04-15`) postdates `2026-03-02`.<br>❌ **Logo Floor:** $410 < 500$ logos. | ⚠️ **Exclude from Base RFI / Request Exception:** Highlight in roadmap or request GA cutoff attestation waiver |
| **Cloud Legacy Code Helper (Deprecated)** | `2022-06-01` | $\$12,000,000$ | $15.0\%$ | $210$ | ❌ **Revenue Floor:** $\$12\text{M} < \$25\text{M}$.<br>❌ **CAGR Floor:** $15\% < 40\%$.<br>❌ **Logo Floor:** $210 < 500$. | ❌ **Exclude from Evaluation:** Deprecated offering (`Decline_Due_To_Score_Risk`) |

### Portfolio Action
* **Primary Submission Track:** Submit **Gemini Code Assist Enterprise** as the core qualifying SKU.
* **Demonstration Allocation:** Prepare one dedicated 60-minute demo package for `Gemini Code Assist Enterprise`. If an exception is granted for `Agent Mode (Preview)`, generate a second distinct 60-minute demo package as required by the multi-product rule.

---

## 3. Dual-Stage Workback Timeline Schedule

When running with both documents, `TimelineEngine` establishes two synchronized critical paths to ensure neither the text attestation nor the video demonstration misses its deadline. All dates respect corporate freeze windows (**Q2 Corporate Earnings Blackout** from `June 8–9` and **Google Cloud Next 2026** from `June 14–16`) and enforce 24-hour executive review buffers.

### Stage 1: RFI Questionnaire & Signed Attestation Path (Deadline: Feb 27, 2026)
| Milestone / Activity | Target Date (UTC/EST) | Lead Role | Deliverable |
| :--- | :---: | :--- | :--- |
| **Automated RAG Ingestion & Pre-population** | `2026-02-10 (17:00 EST)` | `rficonductorv2` | Draft responses pre-populated with purple markdown (`Drafted` status). |
| **SME Curation & Technical Review Deadline** | `2026-02-18 (17:00 EST)` | Domain SMEs | Final technical accuracy sign-off across all 150+ RFI questions. |
| **Consolidated OPM / Legal & Commercial Review** | `2026-02-23 (17:00 EST)` | Legal & OPM | Pricing sheet validation and attestation risk check. |
| **Executive Panel Sign-off (T-2 Buffer)** | `2026-02-25 (17:00 EST)` | Executive VP | Formal signature on threshold attestation document. |
| **Stage 1 Final Portal Submission** | **`2026-02-27 (17:00 EST)`** | Portal Administrator | Upload of signed attestation and completed questionnaire. |

---

### Stage 2: Product Demonstration & TOC Indexing Path (Deadline: March 10, 2026)
| Milestone / Activity | Target Date (UTC/PT) | Lead Role | Deliverable |
| :--- | :---: | :--- | :--- |
| **Use Case & Architecture Storyboard Freeze** | `2026-02-26 (17:00 PT)` | `pm-leadership@` & SMEs | Storyboard aligned to Gartner's mandatory Use Cases & Critical Capabilities. |
| **Terminal Recording & Module Curation** | `2026-03-03 (17:00 PT)` | Domain SMEs (`devops`, `sec`) | Raw 720p+ `.mp4` video recordings of autonomous plan execution & verification. |
| **Roadmap & Improvements Module Recording** | `2026-03-04 (17:00 PT)` | `pm-leadership@` | Video module detailing past-year delivered commitments & realistic 1-year roadmap. |
| **Master Assembly, File Compression & TOC Indexing** | `2026-03-06 (17:00 PT)` | `opm-coordinator@` | Video stitched ($\le 60\text{m}$, $<4\text{GB}$) and separate TOC document authored with exact `[mm:ss]` timecodes. |
| **Executive & Legal Video Review (T-2 Buffer)** | `2026-03-08 (17:00 PT)` | Executive Review Panel | Verification of unreleased roadmap claims and confidentiality boundaries. |
| **Stage 2 Final Portal Upload & Submission** | **`2026-03-10 (23:59 PT)`** | **Portal Administrator Only** | Final upload of `.mp4` demo file(s) and TOC `.docx`/`.pdf` via Gartner Portal dashboard. |

---

## 4. Expanded Dynamic SME & Leadership Task Routing

By processing both inputs, `RoutingEngine` expands beyond text questionnaire triage to dynamically route **multimedia demonstration responsibilities** to domain experts, enforcing a `0.70` confidence threshold.

| Deliverable Type | Section / Topic Area | Assigned SME / Owner | Routing Method | Confidence | Required Output / Task Description |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **RFI Text Section** | `Q[2.1]` Multi-step test verification & autonomous rollback | `devops-sme@google.com` | Keyword/Semantic Match | `84.0%` | Review purple markdown draft; confirm CI/CD test generation accuracy. |
| **RFI Text Section** | `Q[3.4]` Data encryption at rest & Workload Identity IAM | `security-sme@google.com` | Keyword/Semantic Match | `91.0%` | Validate tenant isolation and customer code training boundaries. |
| **Demo Module** | `Demo[1]` Autonomous Plan Generation across Code/Tests | `devops-sme@google.com` | Domain Delivery Routing | `95.0%` | Record 12-minute terminal screencast of agent generating plan, executing tests, and self-correcting. |
| **Demo Module** | `Demo[2]` DevSecOps Architecture & IAM Role Enforcement | `security-sme@google.com` | Domain Delivery Routing | `89.0%` | Record 10-minute walkthrough illustrating native IAM role enforcement and secret scanning in IDE. |
| **Demo Module** | `Demo[3]` Past-Year Improvements & 1-Year Committed Roadmap | `pm-leadership@google.com` | Leadership Routing | `99.0%` | Record 15-minute presentation detailing roadmap commitments met in 2025 and planned 2026 GA milestones. |
| **Indexing Deliverable** | `TOC[Master]` Table of Contents Timecode Mapping | `opm-coordinator@google.com` | Fallback / Orchestration | `100.0%` | Author separate document mapping exact `[mm:ss]` timecodes for every Use Case and Critical Capability. |

---

## 5. Strategic Action Plan for Execution

1. **Lock Primary SKU (`Gemini Code Assist Enterprise`):** Confirm immediately that *Gemini Code Assist Enterprise* is our primary evaluated SKU to ensure clean qualification under the March 2, 2026 GA rules and $\$25\text{M}$ revenue floor.
2. **Launch Dual-Stage Workback Tracks (`TimelineEngine`):** Immediately distribute Stage 1 deadlines (`Feb 27`) to questionnaire SMEs and Stage 2 deadlines (`March 10`) to demo recording owners.
3. **Enforce 60-Minute & 4GB Caps Early:** Instruct all video module owners (`devops-sme@`, `security-sme@`, `pm-leadership@`) to respect strict individual module budgets ($10\text{–}15\text{ mins}$) so the combined master video cleanly clears the 60-minute evaluation cutoff.
4. **Pre-Verify Portal Administrator Access:** Ensure the designated submission lead holds active **Administrator** credentials on the Gartner Provider Information Portal well ahead of the March 10 upload date.
