"""Парсер страниц через Playwright."""

from playwright.sync_api import sync_playwright
from typing import Any
from config import HEADLESS_BROWSER, BROWSER_TYPE


def scrape_page(url: str, selector: str = "body") -> str:
    with sync_playwright() as p:
        browser_type = getattr(p, BROWSER_TYPE)
        browser = browser_type.launch(headless=HEADLESS_BROWSER)
        try:
            page = browser.new_page()
            page.goto(url)
            page.wait_for_load_state("networkidle")
            content = page.inner_html(selector)
            return content
        finally:
            browser.close()


def scrape_with_js(url: str, js_code: str) -> Any:
    with sync_playwright() as p:
        browser_type = getattr(p, BROWSER_TYPE)
        browser = browser_type.launch(headless=HEADLESS_BROWSER)
        try:
            page = browser.new_page()
            page.goto(url)
            page.wait_for_load_state("networkidle")
            result = page.evaluate(js_code)
            return result
        finally:
            browser.close()
