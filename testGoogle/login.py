"""
Run once to authenticate with Google and save the browser session.
Usage: python login.py
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
from config import SESSION_PATH


async def main():
    session_path = Path(SESSION_PATH)

    print("Avvio browser per il login Google...")
    print("Accedi con il tuo account Google Workspace quando si apre il browser.")
    print("Dopo il login, premi INVIO qui per salvare la sessione.\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://accounts.google.com")
        await page.wait_for_url("**/myaccount.google.com/**", timeout=120_000)

        print("Login rilevato. Navigo su Google Vids per completare la sessione...")
        await page.goto("https://vids.google.com")
        await page.wait_for_load_state("networkidle", timeout=30_000)

        # Also visit docs.google.com/videos to set cookies for that domain
        await page.goto("https://docs.google.com/videos/")
        await page.wait_for_load_state("networkidle", timeout=30_000)

        await context.storage_state(path=str(session_path))
        await browser.close()

    print(f"\nSessione salvata in: {session_path}")
    print("Ora puoi avviare il server con: uvicorn main:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
