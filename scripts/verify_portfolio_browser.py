"""Optional real browser QA of the isolated portfolio entry point. Never owner profiles."""

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse


def verify(url, output, axe_script=None, expect_pack_error=False, no_artwork=False):
    from playwright.sync_api import expect, sync_playwright

    output.mkdir(parents=True, exist_ok=True)
    errors, failures, audit, timings = [], [], [], {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            record_video_dir=str(output / "video"),
            record_video_size={"width": 1280, "height": 720},
        )
        page = context.new_page()

        def observe(page):
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("requestfailed", lambda r: failures.append({"url": r.url, "error": r.failure}))

        def open_choice(widget):
            page.locator('[data-testid="stStatusWidget"]').wait_for(state="hidden", timeout=30000)
            page.wait_for_timeout(500)
            widget.locator("xpath=ancestor::*[.//button[@aria-label='Open']][1]").get_by_role(
                "button", name="Open", exact=True
            ).click()

        def expand(page, title):
            label = page.get_by_text(title, exact=True)
            if label.locator("xpath=ancestor::details[1]").get_attribute("open") is None:
                label.click()

        observe(page)

        def ready(page):
            page.get_by_role("button", name="Знайти свою історію", exact=True).wait_for(
                timeout=60000
            )
            expect(
                page.get_by_text("Демонстрація · синтетичний профіль, реальні назви", exact=True)
            ).to_be_visible()
            if (
                no_artwork
                and page.get_by_role(
                    "checkbox", name="Показувати постери", exact=True, include_hidden=True
                ).is_checked()
            ):
                expand(page, "Ваша демосесія")
                page.get_by_text("Показувати постери", exact=True).click()
                expect(
                    page.get_by_role("checkbox", name="Показувати постери", exact=True)
                ).not_to_be_checked()
                page.get_by_text("Ваша демосесія", exact=True).click()

        def screenshot(page, name):
            print(f"Capturing {name}", flush=True)
            page.mouse.wheel(0, -10000)
            page.wait_for_timeout(300)
            page.wait_for_function(
                "() => [...document.images].every(i => i.complete && i.naturalWidth > 0)",
                timeout=30000,
            )
            page.screenshot(path=str(output / name), full_page=True)

        def accessibility(page, name):
            if axe_script:
                page.keyboard.press("Escape")
                page.get_by_role("heading", name="◉ CineMatch", exact=True).click()
                page.wait_for_timeout(400)
                page.add_script_tag(path=str(axe_script))
                result = page.evaluate(
                    "async () => {const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}});return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),passes:r.passes.length,incomplete:r.incomplete.map(v=>({id:v.id,nodes:v.nodes.length}))};}"
                )
                audit.append({"page": name, **result})
                if result["violations"]:
                    (output / "accessibility-failure.json").write_text(
                        json.dumps(audit, indent=2), encoding="utf-8"
                    )
                    raise AssertionError(f"Accessibility violations on {name}")

        start = time.perf_counter()
        page.goto(url)
        ready(page)
        timings["home_ready_ms"] = (time.perf_counter() - start) * 1000
        if expect_pack_error:
            expect(
                page.get_by_text("Підготовлений ML-набір не пройшов перевірку.", exact=False)
            ).to_be_visible()
            screenshot(page, "pack-error.png")
            context.close()
            browser.close()
            return {
                "flows": ["invalid pack visible fallback"],
                "page_errors": errors,
                "request_failures": failures,
            }
        screenshot(page, "desktop-discover.png")
        accessibility(page, "desktop discovery")
        page.get_by_text("Пошук", exact=True).first.click()
        query = page.get_by_role("textbox", name="Назва, рік або частина назви", exact=True)
        query.fill("Інтерстеллар 2014")
        start = time.perf_counter()
        query.press("Enter")
        page.get_by_role("heading", name="Інтерстеллар (2014)", exact=True).wait_for()
        timings["uk_search_ready_ms"] = (time.perf_counter() - start) * 1000
        expand(page, "Фільтри та порядок")
        media = page.get_by_role("combobox", name=re.compile(r"Тип$"))
        open_choice(media)
        page.get_by_role("option", name="Серіали", exact=True).click()
        page.get_by_text("Збігів немає.", exact=False).wait_for()
        open_choice(media)
        page.get_by_role("option", name="Фільми", exact=True).click()
        page.get_by_role("heading", name="Інтерстеллар (2014)", exact=True).wait_for()
        screenshot(page, "desktop-search.png")
        accessibility(page, "filtered Ukrainian search")
        page.get_by_role("button", name="Детальніше", exact=True).first.click()
        page.get_by_role("button", name="← Повернутися", exact=True).wait_for()
        expect(
            page.get_by_role("link", name="Джерело української назви ↗", exact=True)
        ).to_be_visible()
        screenshot(page, "desktop-movie-details.png")
        accessibility(page, "movie details")
        page.get_by_role("button", name="← Повернутися", exact=True).click()
        query = page.get_by_role("textbox", name="Назва, рік або частина назви", exact=True)
        query.fill("Пуститися берега")
        query.press("Enter")
        expand(page, "Фільтри та порядок")
        media = page.get_by_role("combobox", name=re.compile(r"Тип$"))
        open_choice(media)
        page.get_by_role("option", name="Серіали", exact=True).click()
        card = page.locator(".st-key-card_search_-169")
        card.get_by_role("button", name="Детальніше", exact=True).click()
        page.get_by_role("button", name="← Повернутися", exact=True).wait_for()
        screenshot(page, "desktop-series-details.png")
        page.get_by_role("button", name="Дивитися пізніше", exact=True).first.click()
        page.get_by_role("button", name="Прибрати зі списку", exact=True).first.wait_for()
        expand(page, "Ваша демосесія")
        page.get_by_role("button", name="Скасувати останню дію", exact=True).click()
        expect(
            page.get_by_role("button", name="Дивитися пізніше", exact=True).first
        ).to_be_enabled()
        stars = page.get_by_role("slider").first
        stars.focus()
        stars.press("ArrowRight")
        page.get_by_role("button", name="Зберегти оцінку", exact=True).click()
        expect(page.get_by_text("Ваша оцінка · ★ 4.5/5", exact=True)).to_be_visible()
        page.get_by_text("Для вас", exact=True).first.click()
        page.get_by_role("heading", name="Знайомий каталог · Adaptive", exact=True).wait_for()
        page.get_by_role("heading", name="Нові можливості", exact=True).wait_for()
        open_choice(page.get_by_role("combobox", name=re.compile(r"Алгоритм рекомендацій$")))
        page.get_by_role("option", name=re.compile(r"^Collaborative ·")).click()
        page.get_by_role("heading", name="Знайомий каталог · Collaborative", exact=True).wait_for()
        screenshot(page, "desktop-for-you.png")
        accessibility(page, "For You")
        page.get_by_text("Моя бібліотека", exact=True).first.click()
        page.get_by_role("heading", name="Ваша кінополиця", exact=True).wait_for()
        open_choice(page.get_by_role("combobox").first)
        page.get_by_role("option", name="English", exact=True).click()
        page.get_by_role("heading", name="Your cinema shelf", exact=True).wait_for()
        expect(page.get_by_role("radio", name="My Library", exact=True)).to_be_checked()
        screenshot(page, "desktop-library.png")
        accessibility(page, "English library")
        open_choice(page.get_by_role("combobox").first)
        page.get_by_role("option", name="Українська", exact=True).click()
        expect(page.get_by_role("radio", name="Моя бібліотека", exact=True)).to_be_checked()
        # Independent visitor: mutation/rating in A must not appear in B.
        other = browser.new_context(viewport={"width": 1440, "height": 1000})
        second = other.new_page()
        observe(second)
        second.goto(url)
        ready(second)
        second.get_by_text("Пошук", exact=True).first.click()
        second_query = second.get_by_role(
            "textbox", name="Назва, рік або частина назви", exact=True
        )
        second_query.fill("Breaking Bad")
        second_query.press("Enter")
        second.locator(".st-key-card_search_-169").get_by_role(
            "button", name="Детальніше", exact=True
        ).click()
        second.get_by_role("button", name="← Повернутися", exact=True).wait_for()
        expect(second.get_by_text("Ваша оцінка · ★ 4.5/5", exact=True)).to_have_count(0)
        expect(
            second.get_by_role("button", name="Дивитися пізніше", exact=True).first
        ).to_be_enabled()
        page.get_by_role("button", name="Відновити приклад", exact=True).click()
        ready(page)
        page.get_by_role("button", name="Почати з чистого профілю", exact=True).click()
        ready(page)
        expand(page, "Ваша демосесія")
        expect(page.get_by_text("0 у списку · 0 оцінок", exact=True)).to_be_visible()
        page.get_by_text("Для вас", exact=True).first.click()
        page.get_by_text("Оцініть кілька знайомих історій", exact=False).wait_for()
        page.reload()
        ready(page)
        expect(page.get_by_text("0 у списку · 0 оцінок", exact=True)).to_have_count(0)
        # Offline internet scenario: posters disabled and external HTTPS blocked;
        # the local Streamlit websocket remains available.
        expand(page, "Ваша демосесія")
        if page.get_by_role("checkbox", name="Показувати постери", exact=True).is_checked():
            page.get_by_text("Показувати постери", exact=True).click()
        expect(
            page.get_by_role("checkbox", name="Показувати постери", exact=True)
        ).not_to_be_checked()
        blocked = []

        def block_remote(route):
            blocked.append(route.request.url)
            route.abort()

        context.route("https://**/*", block_remote)
        page.get_by_text("Пошук", exact=True).first.click()
        query = page.get_by_role("textbox", name="Назва, рік або частина назви", exact=True)
        query.fill("Останні з нас")
        query.press("Enter")
        page.locator(".st-key-card_search_-46562").get_by_role(
            "button", name="Детальніше", exact=True
        ).click()
        page.get_by_role("button", name="← Повернутися", exact=True).wait_for()
        assert not blocked, "Offline browsing attempted a remote request"
        button = page.get_by_role("button", name="Відновити приклад", exact=True)
        button.focus()
        button.press("Tab")
        focus = page.evaluate(
            "() => {const e=document.activeElement,s=getComputedStyle(e);return {tag:e.tagName,label:e.innerText||e.getAttribute('aria-label'),outline:s.outlineStyle,width:s.outlineWidth,shadow:s.boxShadow};}"
        )
        assert focus["tag"] in ("BUTTON", "INPUT", "A") and (
            focus["outline"] != "none" or focus["shadow"] != "none"
        )
        context.close()
        other.close()
        viewports = []
        for width, height, label in [(390, 844, "mobile"), (768, 1024, "tablet")]:
            responsive = browser.new_context(viewport={"width": width, "height": height})
            small = responsive.new_page()
            observe(small)
            small.goto(url)
            ready(small)
            assert small.evaluate("document.documentElement.scrollWidth <= innerWidth+1"), (
                f"{label} overflow"
            )
            screenshot(small, f"{label}-discover.png")
            small.get_by_text("Пошук", exact=True).first.click()
            q = small.get_by_role("textbox", name="Назва, рік або частина назви", exact=True)
            q.fill("Останні з нас")
            q.press("Enter")
            small.locator(".st-key-card_search_-46562").get_by_role(
                "button", name="Детальніше", exact=True
            ).click()
            small.get_by_role("button", name="← Повернутися", exact=True).wait_for()
            screenshot(small, f"{label}-details.png")
            accessibility(small, f"{label} details")
            assert small.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
            viewports.append([width, height])
            responsive.close()
        version = browser.version
        browser.close()
    if errors or failures:
        raise RuntimeError(json.dumps({"page_errors": errors, "request_failures": failures}))
    return {
        "browser": "Chromium",
        "version": version,
        "viewports": [[1440, 1000], *viewports],
        "flows": [
            "first launch",
            "discovery",
            "Ukrainian/year search",
            "media filters/no results",
            "movie/series details",
            "watchlist",
            "Undo",
            "rating",
            "original ML + heuristic sections",
            "library",
            "UK/EN/UK language",
            "independent visitors",
            "reset",
            "empty profile",
            "refresh reset",
            "offline metadata",
            "keyboard focus",
            "mobile/tablet navigation",
        ],
        "timings": timings,
        "page_errors": errors,
        "request_failures": failures,
        "accessibility": audit,
        "keyboard_focus": focus,
        "scope": "Actual local session-isolated demo/public ML pack. Internet-offline means disabled artwork plus blocked external HTTPS with working localhost. Automated checks are not WCAG certification. Videos are unedited silent QA capture, not a narrated finished presentation.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8514")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--axe-script", type=Path)
    parser.add_argument("--isolated-demo", action="store_true")
    parser.add_argument("--expect-pack-error", action="store_true")
    parser.add_argument(
        "--no-artwork", action="store_true", help="Capture without third-party artwork"
    )
    args = parser.parse_args()
    parsed = urlparse(args.url)
    if (
        not args.isolated_demo
        or parsed.hostname not in ("127.0.0.1", "localhost")
        or parsed.scheme != "http"
    ):
        parser.error("Use only a local dedicated portfolio server and --isolated-demo")
    result = verify(args.url, args.output, args.axe_script, args.expect_pack_error, args.no_artwork)
    (args.output / "browser-results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
