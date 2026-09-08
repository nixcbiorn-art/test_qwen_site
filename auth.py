"""Модуль авторизации через Playwright."""

from playwright.sync_api import sync_playwright
from config import LOGIN_URL, USERNAME, PASSWORD, HEADLESS_BROWSER, BROWSER_TYPE


def get_auth_token():
    with sync_playwright() as p:
        browser_type = getattr(p, BROWSER_TYPE)
        browser = browser_type.launch(headless=HEADLESS_BROWSER)

        try:
            page = browser.new_page()
            page.goto(LOGIN_URL)

            # АДАПТИРУЙ СЕЛЕКТОРЫ ПОД СВОЙ САЙТ
            page.fill('input[name="username"]', USERNAME)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[type="submit"]')

            page.wait_for_url("**/dashboard**", timeout=10000)

            token = page.evaluate("""() => {
                return localStorage.getItem('auth_token') ||
                       document.cookie.match(/token=([^;]+)/)?.[1];
            }""")

            if not token:
                raise Exception("Токен не найден")

            return token

        finally:
            browser.close()


if __name__ == "__main__":
    token = get_auth_token()
    print(f"Получен токен: {token[:20]}...")
