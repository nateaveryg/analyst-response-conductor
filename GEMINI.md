# Project Governance & Engineering Rules: Analyst Response Agent (ARA)

## Mandatory Engineering Rule: Adversarial & Security Testing

### 🛡️ Adversarial Test Maintenance & Execution Requirement
Whenever making ANY changes to the application (including backend routes, A2UI generative surfaces, frontend DOM renderers, form bindings, or state management):

1. **Review & Update Adversarial Tests:**
   * Review `tests/test_ui_adversarial_agent.py` and ensure coverage for newly added components, action IDs, input fields, and URL handlers.
   * Verify protections against:
     - Cross-Site Scripting (XSS) in Markdown rendering, image tags, and custom links (`javascript:`, `vbscript:`, `data:`).
     - Prototype pollution in client-side state stores (`formContextStore`).
     - Malformed, truncated, or corrupted `<a2ui-json>` protocol blocks.
     - Out-of-bounds state values (negative/extreme phases, percentages, NaN).
     - Network failure / API abort resilience without frozen UI spinners.
     - Path traversal or malicious property injection in data bindings.

2. **Mandatory Test Execution Before Merging / Deploying:**
   * ALWAYS execute the adversarial and full regression test suite:
     ```bash
     .venv/bin/pytest tests/test_ui_adversarial_agent.py -v
     .venv/bin/pytest tests/ -v
     ```
   * Ensure 100% passing test status (0 failures) before concluding any task or deploying releases.

3. **CI/CD Quality Gate:**
   * Cloud Build (`cloudbuild.yaml`) strictly enforces that all unit, integration, Playwright UI, and adversarial test suites pass in Step 1 before creating container images or deploying to Cloud Run.
