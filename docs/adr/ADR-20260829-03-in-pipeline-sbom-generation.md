# Architectural Decision Record (ADR): In-Pipeline SBOM Generation & Artifact Analysis Registration

> **ADR ID:** ADR-20260829-03  
> **Status:** Accepted  
> **Date:** 2026-08-29  
> **Deciders:** Engineering Lead & Security/DevSecOps Team  
> **Scope:** Google Cloud Build Pipelines (`cloudbuild-v3.yaml`, `cloudbuild-frontend.yaml`, `cloudbuild-runner.yaml`)

---

## 1. Context and Problem Statement

Cloud Build artifacts currently lack Software Bill of Materials (SBOM) metadata. Investigation revealed that:
1. **Provenance vs. SBOM**: Cloud Build generates SLSA Build Provenance (v1) by default, but does not generate SBOMs automatically.
2. **Distroless Scanning Barrier**: Conductor v3 uses `gcr.io/distroless/static-debian12`, which lacks OS package manager databases (`/var/lib/dpkg/status`). Consequently, Artifact Analysis cannot generate a post-push `DISCOVERY` occurrence, causing `gcloud artifacts sbom export` to fail.
3. **Missing In-Pipeline Automation**: No build step currently scans compiled binaries, Go modules, or container layers to generate and attach an SBOM file (`sbom.spdx.json`) to Artifact Registry.

---

## 2. Decision

We will **generate SBOMs directly within Cloud Build pipelines** and register them in **Artifact Analysis**:

1. **In-Pipeline Tooling (`syft`)**:
   - Add a containerized build step utilizing `anchore/syft:v1.18.1` to generate a standardized **SPDX 2.3 JSON** SBOM (`sbom.spdx.json`) from the built container image, embedded Go binaries, and dependency manifests.

2. **Artifact Analysis Registration (`gcloud artifacts sbom load`)**:
   - Add a Cloud SDK build step executing `gcloud artifacts sbom load --source=sbom.spdx.json --uri=...` to upload the SBOM to Cloud Storage and create an official `SBOM_REFERENCE` occurrence linked to the container image digest in Artifact Registry.

3. **Cloud Build Artifact Archival (`artifacts.objects`)**:
   - Archive `sbom.spdx.json` into Google Cloud Storage under `gs://${PROJECT_ID}_cloudbuild/sboms/${BUILD_ID}` for direct auditing, compliance verification, and download.

---

## 3. Consequences and Benefits

### Positive Consequences
* **Complete Supply Chain Visibility**: Generates machine-readable software inventory in compliance with Executive Order 14028 and Google Cloud Software Delivery Shield standards.
* **Console & Security Insights Integration**: Surfaces full dependency trees in the Google Cloud Console Artifact Registry and Cloud Build Security Insights dashboard.
* **Bypasses Distroless Limitation**: Inspects the compiled Go binary symbols and vendored modules directly, providing accurate dependency tracking where OS package scanners fail.

### Negative Consequences, Tradeoffs, & Mitigations
* **Build Execution Latency**: Adds ~10–25 seconds to Cloud Build to inspect container layers and upload occurrences.
  * *Mitigation:* Execute SBOM generation conditionally on release tags rather than rapid local feature branches.
* **Information Disclosure Risk**: Publicly accessible SBOMs provide attackers an exact blueprint of vulnerable dependencies and toolchains.
  * *Mitigation:* Restrict Artifact Registry repositories and Cloud Storage buckets behind IAM permissions and VPC Service Controls.
* **Vulnerability Alert Fatigue**: Artifact Analysis scans every dependency against CVE databases, potentially creating triage toil for non-exploitable vulnerabilities in dead code.
  * *Mitigation:* Pair SBOMs with VEX (Vulnerability Exploitability eXchange) statements to filter non-actionable alerts.
* **Metadata & Storage Accumulation**: High-frequency builds generate hundreds of SBOM JSON files over time.
  * *Mitigation:* Configure GCS bucket lifecycle rules with a 60–90 day retention period for build SBOM artifacts.


---

## 4. References
* Google Cloud Artifact Analysis SBOM Documentation: `gcloud artifacts sbom load`
* SPDX 2.3 Specification: `spdx-json`
* Software Delivery Shield Framework
