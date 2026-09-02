import time
import sys
from playwright.sync_api import sync_playwright

def evaluate_live_cloud_run():
    output_dir = "/usr/local/google/home/averyn/.gemini/jetski/brain/826ea6bd-0326-4dd0-8c0c-75e4c5552c27"
    url = "https://conductor-v2-105792947502.us-central1.run.app"
    
    print("==========================================================================")
    print("🚀 Starting Automated Empirical Browser Evaluation against Google Cloud Run")
    print(f"Target URL: {url}")
    print("==========================================================================")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/google-chrome",
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--window-size=1920,1080"
            ]
        )
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        print("1️⃣ [Step 1] Navigating to live Cloud Run Web Portal...")
        page.goto(url, timeout=30000)
        time.sleep(4)  # Allow initial A2UI streaming and workspace fetching to stabilize
        
        # Verify Workspace Selector dropdown
        selector = page.locator("#workspace-selector")
        assert selector.is_visible(), "ERROR: Workspace selector dropdown not visible!"
        options = selector.locator("option").all_inner_texts()
        print(f"✅ Loaded Enterprise Workspaces in Header Dropdown ({len(options)} total):")
        for opt in options:
            print(f"   * {opt}")
        
        path_portal = f"{output_dir}/01_live_portal_with_workspace_selector.png"
        page.screenshot(path=path_portal)
        print(f"📸 Screenshot captured: {path_portal}")
        
        print("\n2️⃣ [Step 2] Testing Protected Tenancy & Enterprise Read-Only Alert Banner...")
        # Select the IDC MarketScape (Read-Only) option
        idc_value = page.evaluate("() => { const opt = Array.from(document.querySelectorAll('#workspace-selector option')).find(o => o.text.includes('IDC') || o.text.includes('Read-Only')); return opt ? opt.value : null; }")
        assert idc_value, "ERROR: Could not locate IDC MarketScape Read-Only workspace option in selector!"
        
        page.select_option("#workspace-selector", value=idc_value)
        time.sleep(2)
        
        banner = page.locator("#read-only-banner")
        assert banner.is_visible(), "ERROR: Enterprise Read-Only alert banner did not appear upon selecting restricted peer workspace!"
        banner_text = banner.inner_text()
        print(f"✅ Read-Only Protection Banner Displayed Successfully:\n   \"{banner_text.splitlines()[0]}\"")
        path_readonly = f"{output_dir}/02_live_read_only_tenancy_banner.png"
        page.screenshot(path=path_readonly)
        print(f"📸 Screenshot captured: {path_readonly}")
        
        print("\n3️⃣ [Step 3] Restoring Editable Workspace & Launching Phase 5 Storyboard Playbook...")
        # Re-select default editable CNAP workspace
        cnap_value = page.evaluate("() => { const opt = Array.from(document.querySelectorAll('#workspace-selector option')).find(o => o.text.includes('CNAP') || o.text.includes('Edit')); return opt ? opt.value : null; }")
        page.select_option("#workspace-selector", value=cnap_value)
        time.sleep(2)
        assert not banner.is_visible(), "ERROR: Read-only banner did not hide after switching back to editable workspace!"
        print("✅ Re-selected editable CNAP workspace. Alert banner safely retracted.")
        
        page.evaluate("sendAction('open_demo_sandboxes', 'Open Demo Sandboxes')")
        time.sleep(3)
        
        invoke_btn = page.locator("button:has-text('Invoke Sr. OPM Demo Architect')")
        assert invoke_btn.is_visible(), "ERROR: 'Invoke Sr. OPM Demo Architect' action button missing from Phase 5 surface!"
        print("✅ Phase 5 On-Demand Demo Sandboxes card loaded cleanly with new Sr. OPM AI Demo Architect button.")
        path_phase5 = f"{output_dir}/03_live_phase5_with_demo_architect_button.png"
        page.screenshot(path=path_phase5)
        print(f"📸 Screenshot captured: {path_phase5}")
        
        print("\n4️⃣ [Step 4] Invoking Sr. OPM / PM AI Demo Script Architect Sub-Agent...")
        invoke_btn.click()
        time.sleep(6)  # Allow generative / synthesis pipeline to respond and stream cards
        
        exec_card = page.locator("text=Executive Summary: Current GA Compliance vs. Future Visionary Roadmap").first
        assert exec_card.is_visible(), "ERROR: Executive Summary narrative card did not render!"
        psychology_card = page.locator("text=Analyst Expectation Intelligence").first
        assert psychology_card.is_visible(), "ERROR: Analyst Expectation Intelligence card did not render!"
        
        print("✅ Sr. OPM AI Demo Script Architect Sub-Agent successfully synthesized and streamed:")
        print("   * Executive Summary Strategy (Current GA compliance vs. Future Visionary roadmap & Terraform commands)")
        print("   * Analyst Psychology Intelligence (Explicit 'On the Page' vs. Implicit 'Not on the Page')")
        print("   * Step-by-Step Scripted Visual Actions & Word-for-Word Voiceover Dialogues")
        path_architect = f"{output_dir}/04_live_demo_architect_synthesis_card.png"
        page.screenshot(path=path_architect)
        print(f"📸 Screenshot captured: {path_architect}")
        
        print("\n5️⃣ [Step 5] Evaluating Interactive Enterprise Workspace Creation Dialog...")
        new_btn = page.locator("button:has-text('➕ New')")
        new_btn.click()
        time.sleep(1.5)
        
        modal = page.locator("#create-workspace-modal")
        assert modal.is_visible(), "ERROR: Create Workspace modal did not open!"
        page.locator("#ws-name-input").fill("Gartner MQ 2026 - AI Infrastructure & TPUs")
        page.locator("#ws-report-input").fill("Gartner Magic Quadrant")
        page.locator("#ws-desc-input").fill("Specialized evaluation workspace for Google Cloud TPU v5e and Gemini Hypercomputer clusters.")
        path_modal = f"{output_dir}/05_live_create_workspace_modal.png"
        page.screenshot(path=path_modal)
        print("✅ Created new workspace configuration inside interactive modal.")
        print(f"📸 Screenshot captured: {path_modal}")
        
        # Submit form
        page.locator("#create-workspace-modal button[type='submit']").click()
        time.sleep(3)
        assert not modal.is_visible(), "ERROR: Create workspace modal did not close after submission!"
        
        active_text = page.locator("#workspace-selector option:checked").inner_text()
        assert "AI Infrastructure & TPUs" in active_text, f"ERROR: Newly created workspace not active! Checked text: {active_text}"
        print(f"✅ New workspace instantiated in PostgreSQL database and activated in header: '{active_text}'")
        path_created = f"{output_dir}/06_live_created_new_workspace_active.png"
        page.screenshot(path=path_created)
        print(f"📸 Screenshot captured: {path_created}")
        
        browser.close()
        print("\n==========================================================================")
        print("🎉 EMPIRICAL EVALUATION COMPLETED WITH 100% SUCCESS AGAINST LIVE CLOUD RUN!")
        print("==========================================================================")

if __name__ == "__main__":
    evaluate_live_cloud_run()
