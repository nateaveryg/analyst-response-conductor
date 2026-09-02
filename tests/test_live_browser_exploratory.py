import os
import sys
import time
from playwright.sync_api import sync_playwright

def test_live_cloud_run():
    target_url = "https://conductor-v3-prod-105792947502.us-central1.run.app"
    print(f"Testing live Cloud Run at {target_url}")
    
    console_logs = []
    page_errors = []
    network_requests = []
    failed_requests = []

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

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        
        def handle_response(res):
            network_requests.append({
                "url": res.url,
                "status": res.status,
                "content_type": res.headers.get("content-type", "")
            })
            if res.status >= 400:
                failed_requests.append({
                    "url": res.url,
                    "status": res.status,
                    "content_type": res.headers.get("content-type", "")
                })

        page.on("response", handle_response)

        print("Navigating to page...")
        response = page.goto(target_url, wait_until="networkidle", timeout=60000)
        print(f"Initial navigation response status: {response.status if response else 'None'}")

        time.sleep(5) # wait for flutter initialization and API calls

        title = page.title()
        print(f"Page title: {title}")

        # Check DOM content
        content = page.content()
        print(f"DOM content length: {len(content)}")
        
        # Check elements
        has_flutter_view = page.locator("flutter-view").count()
        has_flt_glass_pane = page.locator("flt-glass-pane").count()
        print(f"flutter-view count: {has_flutter_view}, flt-glass-pane count: {has_flt_glass_pane}")

        # Take screenshot
        os.makedirs("test_artifacts", exist_ok=True)
        screenshot_path = "test_artifacts/initial_load.png"
        page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")

        print(f"\nTotal network requests: {len(network_requests)}")
        print(f"Total failed requests: {len(failed_requests)}")
        for fr in failed_requests:
            print(f"  FAILED: {fr['status']} - {fr['url']}")

        print(f"\nTotal console logs: {len(console_logs)}")
        for cl in console_logs:
            print(f"  CONSOLE: {cl}")

        print(f"\nTotal page errors: {len(page_errors)}")
        for pe in page_errors:
            print(f"  ERROR: {pe}")

        browser.close()

if __name__ == "__main__":
    test_live_cloud_run()
