import time
from playwright.sync_api import sync_playwright

def inspect_flutter_dom():
    target_url = "https://conductor-v3-prod-105792947502.us-central1.run.app"
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
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(target_url, wait_until="networkidle")
        time.sleep(4)

        # Inspect flutter view inner HTML
        inner_html = page.evaluate("document.querySelector('flutter-view') ? document.querySelector('flutter-view').innerHTML : 'No flutter-view'")
        print("Flutter view inner HTML preview (first 1000 chars):")
        print(inner_html[:1000])

        # Check for semantics placeholder
        placeholder = page.locator("flt-semantics-placeholder")
        print(f"Semantics placeholder count: {placeholder.count()}")
        if placeholder.count() > 0:
            print("Activating semantics placeholder...")
            placeholder.click()
            time.sleep(2)
            semantics_html = page.evaluate("document.querySelector('flt-semantics-host') ? document.querySelector('flt-semantics-host').innerHTML : 'No semantics-host'")
            print("Semantics host HTML preview (first 1500 chars):")
            print(semantics_html[:1500])

        browser.close()

if __name__ == "__main__":
    inspect_flutter_dom()
