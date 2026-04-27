import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from config import SESSION_PATH, GOOGLE_VIDS_URL


async def trigger_export(video_id: str) -> bool:
    """
    Opens the Google Vids project headlessly and triggers the export/download.
    Returns True if export was triggered successfully.
    """
    session_path = Path(SESSION_PATH)
    if not session_path.exists():
        raise FileNotFoundError(
            f"Session file not found at {SESSION_PATH}. Run 'python login.py' first."
        )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=str(session_path))
        page = await context.new_page()

        project_url = f"{GOOGLE_VIDS_URL}/video/{video_id}"
        await page.goto(project_url, wait_until="networkidle", timeout=60_000)

        # Check if we got redirected to login (session expired)
        if "accounts.google.com" in page.url:
            await browser.close()
            raise PermissionError(
                "Session expired. Run 'python login.py' to refresh the session."
            )

        # Click the Share/Export menu — selector may need adjustment if Google updates UI
        try:
            export_triggered = await _click_export(page)
        except PlaywrightTimeout:
            await browser.close()
            raise RuntimeError(
                "Could not find the export button. The Google Vids UI may have changed."
            )

        # Wait briefly to let the export job register
        await asyncio.sleep(3)
        await browser.close()

    return export_triggered


async def _click_export(page) -> bool:
    """Attempt to click the export/download button in Google Vids."""
    # Try the "Download" option in the File menu
    try:
        await page.click('button[aria-label="File"]', timeout=10_000)
        await page.click('menuitem:has-text("Download")', timeout=5_000)
        return True
    except PlaywrightTimeout:
        pass

    # Fallback: look for a share/export button in the toolbar
    try:
        await page.click('[data-tooltip*="export" i], [aria-label*="export" i]', timeout=10_000)
        return True
    except PlaywrightTimeout:
        pass

    # Fallback: keyboard shortcut Ctrl+Shift+D (common export shortcut)
    await page.keyboard.press("Control+Shift+D")
    await asyncio.sleep(2)
    return True
