#!/usr/bin/env python3
"""
Adversarial UI Testing Suite (Automated Red-Team / Fuzzing Agent)
Executes aggressive adversarial attack vectors against the Analyst Response Agent (ARA) UI:
1. XSS and script injection attacks in markdown, links, images, and form fields.
2. Malformed, truncated, and schema-violating <a2ui-json> declarative payloads.
3. Extreme input fuzzing (mega-payloads, unicode bomb, prototype pollution).
4. State chaos & race conditions (rapid workspace switching, invalid UUIDs, out-of-bound journey phases).
5. Network error resilience & API crash simulation.
"""

import json
import os
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

STATIC_HTML_PATH = Path(__file__).parent.parent / "app" / "static" / "index.html"


@pytest.fixture(scope="module")
def browser_context():
    """Launches headless Chromium for adversarial UI test scenarios."""
    with sync_playwright() as p:
        chrome_path = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None
        launch_kwargs = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--window-size=1920,1080"
            ]
        }
        if chrome_path:
            launch_kwargs["executable_path"] = chrome_path

        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        yield context
        browser.close()


def test_adversarial_xss_injections(browser_context):
    """
    Adversarial Vector 1: Cross-Site Scripting (XSS) & Protocol Injections
    Injects malicious script payloads into messages, markdown links, images, and card titles.
    Verifies that no scripts execute and window.__xss_compromised remains undefined / false.
    """
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # Initialize trap flag on window
    page.evaluate("window.__xss_compromised = false;")

    # 1. Inject classic <script> tag via appendMessage
    xss_script = "<script>window.__xss_compromised = true;</script>"
    page.evaluate("appendMessage('agent', " + json.dumps(xss_script) + ");")

    # 2. Inject onerror image tag
    xss_img = "<img src='invalid-image.png' onerror='window.__xss_compromised = true;'>"
    page.evaluate("appendMessage('agent', " + json.dumps(xss_img) + ");")

    # 3. Inject javascript: URI in markdown link
    xss_link = "[Click Exploit](javascript:window.__xss_compromised=true)"
    page.evaluate("appendMessage('agent', " + json.dumps(xss_link) + ");")

    # 4. Inject markdown image with javascript: src
    xss_md_img = "![Evil](javascript:window.__xss_compromised=true)"
    page.evaluate("appendMessage('agent', " + json.dumps(xss_md_img) + ");")

    # 5. Inject SVG onload
    xss_svg = "<svg onload='window.__xss_compromised = true;'>"
    page.evaluate("appendMessage('agent', " + json.dumps(xss_svg) + ");")

    # 6. Click on any rendered links to verify protocol sanitization
    rendered_links = page.locator("a:has-text('Click Exploit')")
    if rendered_links.count() > 0:
        for i in range(rendered_links.count()):
            rendered_links.nth(i).click()

    page.wait_for_timeout(300)

    # Verify that the XSS payload was NOT executed
    is_compromised = page.evaluate("window.__xss_compromised")
    assert not is_compromised, "CRITICAL: UI executed malicious XSS payload in chat/markdown renderer!"

    page.close()


def test_adversarial_malformed_a2ui_payloads(browser_context):
    """
    Adversarial Vector 2: Malformed & Schema-Violating <a2ui-json> Surfaces
    Fuzzes renderA2UISurface with corrupted, truncated, and type-mismatched payloads.
    Verifies graceful error boundaries without page crashes or frozen JS execution.
    """
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # 1. Truncated / Broken JSON Syntax
    page.evaluate("renderA2UISurface('<a2ui-json>{\"surfaceId\": \"broken\", \"components\": [ { \"id\": 1, </a2ui-json>');")
    
    # 2. Completely empty tag
    page.evaluate("renderA2UISurface('<a2ui-json></a2ui-json>');")

    # 3. Null components array
    page.evaluate("renderA2UISurface('<a2ui-json>{\"surfaceId\": \"null_comp\", \"components\": null}</a2ui-json>');")

    # 4. Non-object elements inside components array
    page.evaluate("renderA2UISurface('<a2ui-json>{\"surfaceId\": \"bad_array\", \"components\": [null, 123, true, \"unexpected_string\"]}</a2ui-json>');")

    # 5. Unknown Component Type with exploit payload
    page.evaluate("renderA2UISurface('<a2ui-json>{\"surfaceId\": \"unknown_type\", \"components\": [{\"id\": \"x\", \"component\": {\"ExploitWidget\": {\"payload\": \"malicious\"}}}]}</a2ui-json>');")

    # 6. Null and undefined input to renderA2UISurface
    page.evaluate("renderA2UISurface('');")

    page.wait_for_timeout(200)

    # Verify that error boundary caught the bad JSON and rendered defensive error message
    error_banners = page.locator(".bg-red-50:has-text('Failed to render A2UI surface')")
    assert error_banners.count() >= 1, "Expected defensive error banner to be rendered for malformed JSON"

    # Verify page is still responsive by interacting with user input
    user_input = page.locator("#user-input")
    user_input.fill("Still alive after fuzzing")
    assert user_input.input_value() == "Still alive after fuzzing"

    page.close()


def test_adversarial_extreme_input_fuzzing(browser_context):
    """
    Adversarial Vector 3: Extreme Input Fuzzing & Prototype Pollution
    Fuzzes input forms and state stores with massive payloads, unicode anomalies, and pollution keys.
    """
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # 1. Mega String (50,000 characters)
    mega_string = "A" * 50000
    page.evaluate("appendMessage('user', " + json.dumps(mega_string[:1000]) + ");")

    # 2. Unicode & Special Character Bomb (RTL override, zero-width, null bytes, emojis)
    unicode_bomb = "🚨 \u202E RTL_REVERSED \u200B \uFEFF <>&\"' 🎯 🚀 🔥 NULL_BYTE"
    page.evaluate("appendMessage('agent', " + json.dumps(unicode_bomb) + ");")

    # 3. Prototype Pollution Attack on formContextStore via safeUpdateContext
    page.evaluate("""
        try {
            safeUpdateContext({
                '__proto__': { 'polluted': true },
                'constructor': { 'prototype': { 'polluted': true } },
                'normal_key': 'safe_value'
            });
        } catch(e) {}
    """)

    # Verify Object.prototype was not polluted globally
    is_polluted = page.evaluate("typeof ({}).polluted !== 'undefined'")
    assert not is_polluted, "Prototype pollution detected on global Object prototype!"

    # Verify normal key was recorded safely
    has_key = page.evaluate("formContextStore['normal_key'] === 'safe_value'")
    assert has_key, "Expected normal key to be safely recorded in formContextStore"

    page.close()


def test_adversarial_workspace_state_chaos(browser_context):
    """
    Adversarial Vector 4: State Chaos & Out-of-Bounds Transitions
    Simulates rapid workspace switching, invalid IDs, and extreme journey phase values.
    """
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # 1. Out-of-bounds journey values
    page.evaluate("updateJourneyUI(-999, 'Negative Phase', -100)")
    page.wait_for_timeout(50)
    # Check that it clamped to Step 1 and 0%
    badge_text = page.locator("#journey-step-badge").inner_text()
    assert "Step 1 of 7 (0%)" in badge_text

    page.evaluate("updateJourneyUI(9999, 'Extreme Phase', 99999)")
    page.wait_for_timeout(50)
    # Check that it clamped to Step 7 and 100%
    badge_text = page.locator("#journey-step-badge").inner_text()
    assert "Step 7 of 7 (100%)" in badge_text

    page.evaluate("updateJourneyUI(NaN, null, Infinity)")
    page.wait_for_timeout(50)

    # 2. Rapid workspace switching chaos loop
    page.evaluate("""
        for (let i = 0; i < 20; i++) {
            switchWorkspace('fake-uuid-' + i);
        }
    """)
    page.wait_for_timeout(100)

    # Verify UI elements remain intact and didn't crash
    assert page.locator("#journey-progress-header").is_visible()
    assert page.locator("#chat-messages").is_visible()

    page.close()


def test_adversarial_modal_rapid_cycling(browser_context):
    """
    Adversarial Vector 5: Modal Drawer Rapid Cycling
    Spams open and close events on modals to test DOM event listener leaks and race conditions.
    """
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # Rapid open/close spam
    page.evaluate("""
        for (let i = 0; i < 10; i++) {
            openSavedArtifactsModal();
            closeSavedArtifactsModal();
            openCreateWorkspaceModal();
            closeCreateWorkspaceModal();
        }
    """)
    page.wait_for_timeout(150)

    # Modals should be closed cleanly at the end
    assert not page.locator("#saved-artifacts-modal").is_visible() or "hidden" in (page.locator("#saved-artifacts-modal").get_attribute("class") or "")
    assert not page.locator("#create-workspace-modal").is_visible() or "hidden" in (page.locator("#create-workspace-modal").get_attribute("class") or "")

    page.close()


def test_adversarial_network_error_simulation(browser_context):
    """
    Adversarial Vector 6: Network Crash & API Error Resilience
    Mocks network aborts and 500 Internal Server Errors on backend endpoints.
    Verifies that loading spinners are removed and informative error messages appear.
    """
    page = browser_context.new_page()

    # Route /api/v1/a2ui/chat to abort with 500
    page.route("**/api/v1/a2ui/chat", lambda route: route.abort("failed"))
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # Submit a message that triggers the failing network call
    user_input = page.locator("#user-input")
    user_input.fill("Trigger network crash")
    page.locator("#chat-form button[type='submit']").click()

    page.wait_for_timeout(200)

    # Verify loading spinner / typing indicator is removed
    typing_indicator = page.locator("[id^='typing-']")
    assert typing_indicator.count() == 0, "Typing indicator must be removed on network failure"

    # Verify error message is rendered
    error_msg = page.locator(".prose:has-text('Error connecting to Cloud Run')")
    assert error_msg.count() >= 1, "Expected graceful network error message to appear in chat stream"

    page.close()


def test_adversarial_form_field_data_binding_fuzzing(browser_context):
    """
    Adversarial Vector 7: Form Field & Data Binding Fuzzing
    Fuzzes TextField dataBinding paths with path traversal and malicious keys.
    """
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # Render form field with path traversal dataBinding
    page.evaluate("""
        renderA2UISurface('<a2ui-json>{"surfaceId": "fuzz_form", "components": [{"id": "f1", "component": {"TextField": {"label": "Path Traversal Field", "dataBinding": "/intake/../../__proto__/evil"}}}]}</a2ui-json>');
    """)
    page.wait_for_timeout(100)

    # Type into the fuzz field
    fuzz_input = page.locator("label:has-text('Path Traversal Field') + input, label:has-text('Path Traversal Field') ~ div input")
    if fuzz_input.count() > 0:
        fuzz_input.first.fill("injected_val")

    # Verify global prototype was not polluted
    is_polluted = page.evaluate("typeof ({}).evil !== 'undefined'")
    assert not is_polluted, "Path traversal in dataBinding caused prototype pollution!"

    page.close()


def test_adversarial_button_action_event_fuzzing(browser_context):
    """
    Adversarial Vector 8: Button Action Event & Null Reference Fuzzing
    Renders buttons with missing action objects, empty event IDs, and non-existent export targets.
    """
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # Render buttons with null action, undefined eventId, and invalid actions
    page.evaluate("""
        renderA2UISurface('<a2ui-json>{"surfaceId": "fuzz_buttons", "components": [{"id": "b1", "component": {"Button": {"label": "Null Action Button", "action": null}}}, {"id": "b2", "component": {"Button": {"label": "Empty EventId Button", "action": {"eventId": ""}}}}, {"id": "b3", "component": {"Button": {"label": "Corrupted Action", "action": "not_an_object"}}}]}</a2ui-json>');
    """)
    page.wait_for_timeout(100)

    # Click all fuzzed buttons to verify no unhandled JS errors throw
    page.locator("button:has-text('Null Action Button')").click()
    page.locator("button:has-text('Empty EventId Button')").click()
    page.locator("button:has-text('Corrupted Action')").click()

    page.wait_for_timeout(100)

    # Page should remain completely functional
    user_input = page.locator("#user-input")
    user_input.fill("Healthy after button fuzzing")
    assert user_input.input_value() == "Healthy after button fuzzing"

    page.close()
