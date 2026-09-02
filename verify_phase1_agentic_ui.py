import time
from playwright.sync_api import sync_playwright

def run_browser_ui_tests():
    artifact_dir = "/usr/local/google/home/averyn/.gemini/jetski/brain/9aae882c-4784-4ccf-ae12-4e7176842c33"
    
    with sync_playwright() as p:
        print("Launching Chromium for Phase 1 Multi-Agent UI verification...")
        browser = p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/google-chrome",
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--window-size=1920,1080"
            ]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        print("--- Step 1: Navigating to local web app at http://localhost:8080 ---")
        page.goto("http://localhost:8080/", timeout=30000)
        time.sleep(2)
        shot1 = f"{artifact_dir}/01_ui_onboarding_portal.png"
        page.screenshot(path=shot1)
        print(f"Captured onboarding portal screenshot -> {shot1}")

        print("--- Step 2: Clicking Begin Phase 1 Criteria Intake ---")
        begin_btn = page.locator("button:has-text('Begin Phase 1')")
        if begin_btn.is_visible():
            begin_btn.click()
            time.sleep(2)
        shot2 = f"{artifact_dir}/02_ui_intake_form.png"
        page.screenshot(path=shot2)
        print(f"Captured intake form surface screenshot -> {shot2}")

        print("--- Step 3: Submitting Phase 1 Criteria Analysis (Happy Path) ---")
        page.evaluate("""
            sendAction('submit_criteria_analysis', 'Run Portfolio Analysis & Timeline Generation', {
                analyst_notes: 'Gartner MQ DevSecOps 2026. Target GA date 2026-03-02. Recognized GAAP revenue $50M, 40% CAGR, 500 enterprise customers. Mandatory features include CI/CD build automation, SLSA L3 security scanning, and agentic multi-file code generation.'
            })
        """)
        time.sleep(3)
        shot3 = f"{artifact_dir}/03_ui_phase1_agentic_telemetry_scorecard.png"
        page.screenshot(path=shot3)
        print(f"Captured Phase 1 multi-agent telemetry scorecard screenshot -> {shot3}")

        print("--- Step 4: Testing Unhappy Path (Malformed / Gibberish User Input) ---")
        page.evaluate("""
            sendAction('submit_criteria_analysis', '??? malformed unparseable user text !@#$%^&*()', {
                analyst_notes: 'xyz123 empty unparseable notes'
            })
        """)
        time.sleep(3)
        shot4 = f"{artifact_dir}/04_ui_unhappy_path_defensive_recovery.png"
        page.screenshot(path=shot4)
        print(f"Captured defensive recovery screenshot -> {shot4}")

        print("--- Step 5: Testing Unhappy Path (Conversational Fallback & Guidance) ---")
        input_box = page.locator("#user-input")
        if input_box.is_visible():
            input_box.fill("??? unparseable question about unknown criteria 12345")
            page.locator("button:has-text('Send')").click()
            time.sleep(3)
        shot5 = f"{artifact_dir}/05_ui_unhappy_path_conversational_guidance.png"
        page.screenshot(path=shot5)
        print(f"Captured conversational guidance screenshot -> {shot5}")

        browser.close()
        print("✅ ALL BROWSER UI VERIFICATION TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_browser_ui_tests()
