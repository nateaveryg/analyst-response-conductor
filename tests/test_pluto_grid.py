import os
import time
from playwright.sync_api import sync_playwright

def test_pluto_grid():
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

        # Click Phase 4 chip in JourneyStepper (x: 749, y: 132)
        print("Clicking Phase 4 chip...")
        page.mouse.click(749, 132)
        time.sleep(4)

        # Capture screenshot of Phase 4 split-screen with PlutoGrid
        grid_screenshot = "test_artifacts/plutogrid_phase4.png"
        page.screenshot(path=grid_screenshot)
        print(f"PlutoGrid screenshot saved to {grid_screenshot}")

        # Check semantics text for PlutoGrid elements
        grid_text = page.evaluate("() => document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerText : ''")
        print("\n--- SEMANTICS TEXT FOR PHASE 4 PLUTOGRID ---")
        for line in grid_text.splitlines():
            if any(k in line for k in ["PlutoGrid", "Section ID", "Worksheet Tab", "Assigned SME", "Continuous integration", "Gartner", "Forrester", "Alphabet", "All Tabs"]):
                print(f"  [MATCH] {line.strip()}")

        # Also click a tab ChoiceChip, e.g. "Product or Service 1-87" or "Overall Viability 88-92"
        # Let's inspect nodes on screen
        nodes = page.evaluate("""() => {
            const elms = Array.from(document.querySelectorAll('flt-semantics'));
            return elms.map(e => ({
                text: e.innerText,
                rect: e.getBoundingClientRect()
            })).filter(x => x.text && (x.text.includes('Tab') || x.text.includes('PlutoGrid') || x.text.includes('SEC-01')));
        }""")
        print(f"\nPlutoGrid related semantic nodes count: {len(nodes)}")
        for n in nodes[:15]:
            print(n)

        browser.close()

if __name__ == "__main__":
    test_pluto_grid()
