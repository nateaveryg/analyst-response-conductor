import os
import time
from playwright.sync_api import sync_playwright

def test_governance_radar():
    target_url = "https://conductor-v3-prod-105792947502.us-central1.run.app"
    os.makedirs("test_artifacts", exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/google-chrome",
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(target_url, wait_until="networkidle")
        time.sleep(3)

        # Enable semantics
        page.evaluate("() => { const p = document.querySelector('flt-semantics-placeholder'); if (p) p.click(); }")
        time.sleep(2)

        # Click Governance Radar button at (1680, 28)
        print("Clicking Governance Radar button...")
        page.mouse.click(1680, 28)
        time.sleep(3)

        # Screenshot modal
        radar_screenshot = "test_artifacts/governance_radar_modal.png"
        page.screenshot(path=radar_screenshot)
        print(f"Modal screenshot saved to {radar_screenshot}")

        # Check semantics text for modal contents
        modal_text = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")
        print("\n--- SEMANTICS TEXT AFTER OPENING RADAR MODAL ---")
        for line in modal_text.splitlines():
            if line.strip():
                print(f"  {line.strip()}")

        browser.close()

if __name__ == "__main__":
    test_governance_radar()
