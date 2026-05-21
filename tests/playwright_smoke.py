from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


BASE_URL = os.environ.get("KAIROS_BASE_URL", "http://127.0.0.1:5000")
ARTIFACT_DIR = Path(os.environ.get("KAIROS_ARTIFACT_DIR", ".artifacts"))


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1365, "height": 900})

        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Daily loop")).to_be_visible()
        expect(page.get_by_text("Today's commitments")).to_be_visible()
        expect(page.get_by_text("Edit the shape of today")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "today-web.png"), full_page=True)

        page.goto(f"{BASE_URL}/focus", wait_until="networkidle")
        expect(page.locator(".clock")).to_have_text("25:00")
        expect(page.locator("#focus-minutes")).to_have_value("25")
        expect(page.get_by_role("heading", name="Change target")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "focus-web.png"), full_page=True)

        page.goto(f"{BASE_URL}/goals", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Create goal")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "goals-web.png"), full_page=True)

        page.goto(f"{BASE_URL}/weekly", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Weekly", exact=True)).to_be_visible()
        expect(page.get_by_text("Plan realism")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "weekly-web.png"), full_page=True)

        page.goto(f"{BASE_URL}/north-star", wait_until="networkidle")
        expect(page.get_by_role("heading", name="North Star")).to_be_visible()
        expect(page.get_by_text("Life direction")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "north-star-web.png"), full_page=True)

        page.goto(f"{BASE_URL}/season", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Season", exact=True)).to_be_visible()
        expect(page.get_by_text("Edit season")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "season-web.png"), full_page=True)

        page.goto(f"{BASE_URL}/brain", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Brain", exact=True)).to_be_visible()
        expect(page.get_by_text("Question engine")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "brain-web.png"), full_page=True)

        page.goto(f"{BASE_URL}/areas", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Areas")).to_be_visible()
        expect(page.get_by_role("heading", name="Career")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "areas-web.png"), full_page=True)

        page.goto(f"{BASE_URL}/history", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Review", exact=True)).to_be_visible()
        expect(page.get_by_text("3 decisions for next week")).to_be_visible()
        expect(page.get_by_text("Area balance")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "review-web.png"), full_page=True)

        page.goto(f"{BASE_URL}/coach", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Coach", exact=True)).to_be_visible()
        expect(page.get_by_text("Kairos data coach")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "coach-web.png"), full_page=True)

        page.goto(f"{BASE_URL}/research", wait_until="networkidle")
        expect(page.get_by_role("heading", name="Research", exact=True)).to_be_visible()
        expect(page.get_by_role("heading", name="Research question")).to_be_visible()
        page.screenshot(path=str(ARTIFACT_DIR / "research-web.png"), full_page=True)

        mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        mobile.goto(f"{BASE_URL}/", wait_until="networkidle")
        expect(mobile.get_by_role("heading", name="Today", exact=True)).to_be_visible()
        mobile.screenshot(path=str(ARTIFACT_DIR / "today-mobile.png"), full_page=True)

        browser.close()


if __name__ == "__main__":
    main()
