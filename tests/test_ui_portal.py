#!/usr/bin/env python3
"""
Automated Headless Playwright UI Test Suite for Analyst Response Agent (ARA) Web Portal
Validates DOM structure, A2UI executive client components, modal drawers, workspace switcher,
and client-side defensive error trapping without external network dependencies.
"""

import os
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright

STATIC_HTML_PATH = Path(__file__).parent.parent / "app" / "static" / "index.html"

@pytest.fixture(scope="module")
def browser_context():
    """Launches headless Chromium for UI test scenarios."""
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

def test_ui_portal_header_and_workspace_selector(browser_context):
    """Verifies portal header, connection badge, and workspace selector initialization."""
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # 1. Verify Page Title and Header
    title = page.title()
    assert "Analyst Response Agent" in title

    header_text = page.locator("header").inner_text()
    assert "Analyst Response Agent" in header_text

    # 2. Verify Cloud Run Connection Badge
    assert "Cloud Run Connected" in header_text

    # 3. Verify Workspace Selector Dropdown is Present
    workspace_select = page.locator("#workspace-selector")
    assert workspace_select.is_visible()
    page.close()

def test_ui_portal_chat_controls_and_quick_actions(browser_context):
    """Verifies the chat input container, submit button, and quick action buttons."""
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # 1. Chat input textarea
    user_input = page.locator("#user-input")
    assert user_input.is_visible()
    user_input.fill("Test inquiry for criteria extraction")
    assert user_input.input_value() == "Test inquiry for criteria extraction"

    # 2. Chat form submit button (scoped to #chat-form)
    submit_btn = page.locator("#chat-form button[type='submit']")
    assert submit_btn.is_visible()

    # 3. Verify Quick Action Chips
    quick_actions = page.locator("button:has-text('Document Intake Form'), button:has-text('Saved Artifacts')")
    assert quick_actions.count() > 0
    page.close()

def test_ui_saved_artifacts_modal_drawer(browser_context):
    """Verifies opening and closing the right-side Saved Artifacts drawer modal."""
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    modal = page.locator("#saved-artifacts-modal")
    # Modal starts hidden
    assert not modal.is_visible() or "hidden" in (modal.get_attribute("class") or "")

    # Trigger modal open via UI helper or button
    page.evaluate("openSavedArtifactsModal()")
    page.wait_for_timeout(200)

    # Modal should now be visible or have hidden class removed
    modal_class = modal.get_attribute("class") or ""
    assert "hidden" not in modal_class or modal.is_visible()

    # Close modal
    page.evaluate("closeSavedArtifactsModal()")
    page.wait_for_timeout(200)
    modal_class_closed = modal.get_attribute("class") or ""
    assert "hidden" in modal_class_closed
    page.close()

def test_ui_responsive_mobile_viewport(browser_context):
    """Verifies that the UI renders without horizontal breakage on mobile viewports."""
    page = browser_context.new_page()
    page.set_viewport_size({"width": 375, "height": 812})  # iPhone dimensions
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # Verify header still visible
    assert page.locator("header").is_visible()
    # Verify chat input remains visible
    assert page.locator("#user-input").is_visible()
    page.close()

def test_ui_defensive_error_trap_elements(browser_context):
    """Verifies client-side JavaScript contains defensive DOM error trapping handlers."""
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    html_content = page.content()
    # Verify defensive catch blocks are present in DOM
    assert "Failed to render A2UI surface" in html_content
    assert "Error connecting to Cloud Run" in html_content or "formatMarkdown" in html_content
    page.close()


def test_ui_journey_progress_status_bar(browser_context):
    """Verifies 7-Phase Journey Navigation bar, step badges, dynamic progress bar, and pill state transitions."""
    page = browser_context.new_page()
    page.goto(f"file://{STATIC_HTML_PATH.resolve()}")

    # 1. Verify journey header structure
    assert page.locator("#journey-progress-header").is_visible()
    assert page.locator("#journey-step-badge").is_visible()
    assert page.locator("#journey-step-name").is_visible()
    assert page.locator("#journey-progress-bar").is_visible()
    assert page.locator("#journey-percentage-text").is_visible()

    # 2. Verify all 7 phase step pills are present
    for i in range(1, 8):
        assert page.locator(f"#pill-p{i}").count() == 1

    # 3. Simulate step transition via updateJourneyUI
    page.evaluate("updateJourneyUI(4, 'Phase 4B: Automated RAG Ingestion & Initial Technical Drafts', 57)")
    page.wait_for_timeout(100)

    badge_text = page.locator("#journey-step-badge").inner_text()
    assert "Step 4 of 7 (57%)" in badge_text

    step_name = page.locator("#journey-step-name").inner_text()
    assert "Phase 4B: Automated RAG Ingestion & Initial Technical Drafts" in step_name

    pct_text = page.locator("#journey-percentage-text").inner_text()
    assert "57%" in pct_text

    page.close()

