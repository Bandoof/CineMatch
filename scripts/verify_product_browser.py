"""Optional real Chromium QA. Run ONLY against an isolated local test-profile DB.

Install playwright==1.63.0 and its Chromium browser separately from runtime deps.
Screenshots record a running application; deliberate QA clicks are not owner history.
"""

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlparse


def verify(url, output):
    from playwright.sync_api import expect, sync_playwright

    output.mkdir(parents=True, exist_ok=True)
    errors, failures, timings = [], [], {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: failures.append({"url": request.url, "error": request.failure}),
        )
        start = time.perf_counter()
        page.goto(url)
        page.get_by_role("button", name="Знайти свою історію", exact=True).wait_for(timeout=60000)
        timings["home_ready_ms"] = (time.perf_counter() - start) * 1000
        page.wait_for_function(
            "() => [...document.images].every(i => i.complete && i.naturalWidth > 0)", timeout=30000
        )
        page.screenshot(path=str(output / "desktop-discover.png"), full_page=True)
        page.get_by_text("Пошук", exact=True).first.click()
        query = page.get_by_role("textbox", name="Назва, рік або частина назви", exact=True)
        query.fill("The Last of Us")
        start = time.perf_counter()
        query.press("Enter")
        card = page.locator(".st-key-card_search_-46562")
        card.get_by_role("button", name="Детальніше", exact=True).wait_for()
        timings["search_ready_ms"] = (time.perf_counter() - start) * 1000
        card.get_by_role("button", name="Детальніше", exact=True).click()
        page.get_by_role("button", name="← Повернутися", exact=True).wait_for()
        expect(page.get_by_text("У ролях: ", exact=False)).to_be_visible()
        expect(page.locator(".st-key-card_search_-46562")).to_have_count(0)
        page.mouse.wheel(0, -10000)
        page.wait_for_timeout(500)
        page.wait_for_function(
            "() => [...document.images].every(i => i.complete && i.naturalWidth > 0)", timeout=30000
        )
        page.screenshot(path=str(output / "desktop-details.png"), full_page=True)
        page.get_by_role("button", name="Дивитися пізніше", exact=True).first.click()
        page.get_by_role("button", name="Прибрати зі списку", exact=True).first.wait_for()
        page.get_by_role("button", name="Скасувати останню дію", exact=True).click()
        expect(
            page.get_by_role("button", name="Дивитися пізніше", exact=True).first
        ).to_be_enabled()
        page.get_by_role("button", name="Дивитися пізніше", exact=True).first.click()
        page.get_by_role("button", name="Прибрати зі списку", exact=True).first.wait_for()
        stars = page.get_by_role("slider").first
        stars.focus()
        stars.press("ArrowRight")
        page.get_by_role("button", name="Зберегти оцінку", exact=True).click()
        expect(page.get_by_text("Ваша оцінка · ★ 4.5/5", exact=True)).to_be_visible()
        page.get_by_text("Для вас", exact=True).first.click()
        page.get_by_role("heading", name="Кіно у вашому смаку", exact=True).wait_for()
        page.get_by_text("Нові можливості", exact=True).wait_for()
        page.screenshot(path=str(output / "desktop-for-you.png"), full_page=True)
        page.get_by_text("Пошук", exact=True).first.click()
        query = page.get_by_role("textbox", name="Назва, рік або частина назви", exact=True)
        query.fill("Breaking Bad")
        query.press("Enter")
        page.locator(".st-key-card_search_-169").get_by_role(
            "button", name="Дивитися пізніше", exact=True
        ).click()
        page.get_by_text("Моя бібліотека", exact=True).first.click()
        page.get_by_role("heading", name="Ваша кінополиця", exact=True).wait_for()
        page.locator(".st-key-card_library_-169").get_by_role(
            "button", name="Прибрати зі списку", exact=True
        ).wait_for()
        page.get_by_role("combobox").first.click()
        page.get_by_role("option", name="English", exact=True).click()
        page.get_by_role("heading", name="Your cinema shelf", exact=True).wait_for()
        expect(page.locator(".st-key-card_library_-169")).to_have_count(1)
        page.mouse.wheel(0, -10000)
        page.wait_for_timeout(1000)
        page.screenshot(path=str(output / "desktop-library.png"), full_page=True)
        page.reload()
        page.get_by_role("button", name="Find your story", exact=True).wait_for(timeout=60000)
        page.get_by_text("My Library", exact=True).first.click()
        page.locator(".st-key-card_library_-169").get_by_role(
            "button", name="Remove from watchlist", exact=True
        ).wait_for()
        page.get_by_text("1 watchlisted · 1 ratings", exact=True).wait_for()
        context.close()
        mobile = browser.new_context(
            viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
        )
        phone = mobile.new_page()
        phone.on("pageerror", lambda error: errors.append(str(error)))
        phone.goto(url)
        phone.get_by_role("button", name="Find your story", exact=True).wait_for(timeout=60000)
        phone.screenshot(path=str(output / "mobile-discover.png"), full_page=True)
        assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
            "Mobile horizontal overflow"
        )
        phone.get_by_text("Search", exact=True).first.click()
        mobile_query = phone.get_by_role(
            "textbox", name="Title, year or part of a title", exact=True
        )
        mobile_query.fill("The Last of Us")
        mobile_query.press("Enter")
        phone.locator(".st-key-card_search_-46562").get_by_role(
            "button", name="Details", exact=True
        ).click()
        phone.get_by_role("button", name="← Back", exact=True).wait_for()
        expect(phone.locator(".st-key-card_search_-46562")).to_have_count(0)
        phone.mouse.wheel(0, -10000)
        phone.wait_for_timeout(500)
        phone.screenshot(path=str(output / "mobile-details.png"), full_page=True)
        assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
            "Mobile details horizontal overflow"
        )
        mobile.close()
        version = browser.version
        browser.close()
    if errors or failures:
        raise RuntimeError(
            json.dumps({"page_errors": errors, "request_failures": failures}, ensure_ascii=False)
        )
    return {
        "browser": "Chromium",
        "version": version,
        "viewports": [[1440, 1000], [390, 844]],
        "flows": [
            "first launch",
            "discovery",
            "search",
            "details",
            "watchlist",
            "undo",
            "rating",
            "recommendations",
            "library",
            "language switch",
            "reload",
            "autosave restoration",
            "mobile navigation",
        ],
        "timings": timings,
        "page_errors": errors,
        "request_failures": failures,
        "scope": "Real local browser; public catalogs and isolated QA profile. Timings include browser/Streamlit transport; not Windows or ML quality.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8513")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--isolated-profile",
        action="store_true",
        help="Confirm the server uses a disposable QA profile DB, never owner data",
    )
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if (
        not args.isolated_profile
        or parsed.hostname not in ("127.0.0.1", "localhost")
        or parsed.scheme != "http"
    ):
        parser.error("Use a local server and explicitly confirm --isolated-profile.")
    result = verify(args.url, args.output)
    (args.output / "browser-results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
