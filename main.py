from playwright.sync_api import sync_playwright, Playwright
from browserbase import Browserbase
import time

bb = Browserbase(api_key="bb_live_SZy77wqO_O9eJeQ5xx8p97yWrOc")

def run(playwright: Playwright):
    # Create a session on Browserbase
    session = bb.sessions.create(project_id="d36777fa-3f5b-45be-9bf3-2bfddb8d8335")

    # Connect to the remote session
    try:
        chromium = playwright.chromium
        browser = chromium.connect_over_cdp(session.connect_url)
        # browser = chromium.launch(headless=False)
        # context = browser.new_context()
        context = browser.contexts[0]
        page1 = context.pages[0]
        # Open tab 1 - Google
        page1.goto("https://www.google.com")
        print(page1.title())
        time.sleep(2)

        # Open tab 2 - Orby
        page2 = context.new_page()
        page2.goto("https://web-app.orby.ai/")
        print(page2.title())
        page1.bring_to_front()
        time.sleep(2)
        # Open tab 3 - YouTube
        page3 = context.new_page()
        page3.goto("https://www.youtube.com/")
        print(page3.title())
        page2.bring_to_front()
        time.sleep(2)

        page4 = context.new_page()
        page4.goto("https://www.google.com/")
        print(page4.title())
        page3.bring_to_front()
        time.sleep(2)

        page3 = context.new_page()
        page3.goto("https://www.youtube.com/")
        print(page3.title())
        time.sleep(2)
        # Optional: bring tab back to front for visual focus
        page1.bring_to_front()
    finally:
        browser.close()
        # print(f"Session complete! View replay at https://browserbase.com/sessions/{session.id}")

with sync_playwright() as playwright:
    run(playwright)


# p3IzACLkRwbfMbKfrA3gpsxGXJJU1mHpMZ4Xoj66
# p3IzACLkRwbfMbKfrA3gpsxGXJJU1mHpMZ4Xoj66

