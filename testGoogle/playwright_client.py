import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from config import SESSION_PATH, DOWNLOAD_DIR, GOOGLE_VIDS_BASE_URL, GOOGLE_VIDS_HOME_URL

log = logging.getLogger(__name__)


def _session_check():
    if not Path(SESSION_PATH).exists():
        raise FileNotFoundError(
            f"Session file not found: {SESSION_PATH}. Run 'python login.py' first."
        )


def _project_url(video_id: str) -> str:
    return f"{GOOGLE_VIDS_BASE_URL}/{video_id}/edit"


async def list_projects() -> list[dict]:
    """Scrape the Google Vids homepage to list all projects."""
    _session_check()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=SESSION_PATH)
        page = await context.new_page()

        await page.goto(GOOGLE_VIDS_HOME_URL, wait_until="networkidle", timeout=60_000)
        _check_session(page)

        await page.wait_for_selector(
            "[data-item-id], [data-file-id], .docs-homescreen-grid-item",
            timeout=15_000,
        )

        projects = await page.evaluate("""
            () => {
                const items = document.querySelectorAll('[data-item-id], [data-file-id]');
                return Array.from(items).map(el => ({
                    id: el.getAttribute('data-item-id') || el.getAttribute('data-file-id'),
                    name: (
                        el.querySelector('[data-tooltip]')?.getAttribute('data-tooltip')
                        || el.querySelector('title')?.textContent
                        || el.getAttribute('aria-label')
                        || 'Untitled'
                    ).trim(),
                })).filter(p => p.id);
            }
        """)

        await browser.close()
    return projects


async def download_video(video_id: str) -> Path:
    """
    Opens the Google Vids project, waits for generation if needed,
    clicks Download video, and saves the MP4 locally.
    """
    _session_check()

    dest_dir = DOWNLOAD_DIR / "videos"
    dest_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=SESSION_PATH,
            accept_downloads=True,
        )
        page = await context.new_page()

        url = _project_url(video_id)
        log.info("Opening project: %s", url)
        await page.goto(url, wait_until="networkidle", timeout=60_000)
        _check_session(page)

        # Wait for the editor to be ready
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        # If there's a "Genera video" / "Generate" button, click it and wait
        await _maybe_generate(page)

        # Now click Download
        async with page.expect_download(timeout=180_000) as dl_info:
            triggered = await _click_download_video(page)
            if not triggered:
                raise RuntimeError(
                    "Could not find the Download video button. "
                    "The Google Vids UI may have changed."
                )

        download = await dl_info.value
        filename = download.suggested_filename or f"{video_id}.mp4"
        dest_path = dest_dir / filename
        await download.save_as(str(dest_path))
        log.info("Video saved: %s", dest_path)

        await browser.close()
    return dest_path


async def download_images(video_id: str) -> list[Path]:
    """
    Opens the Google Vids project, goes to the Images section,
    and downloads all generated images.
    """
    _session_check()

    dest_dir = DOWNLOAD_DIR / "images"
    dest_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[Path] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=SESSION_PATH,
            accept_downloads=True,
        )
        page = await context.new_page()

        url = _project_url(video_id)
        await page.goto(url, wait_until="networkidle", timeout=60_000)
        _check_session(page)
        await asyncio.sleep(2)

        # Intercept image responses while scrolling
        saved = []

        async def handle_response(response):
            ct = response.headers.get("content-type", "")
            if "image/" in ct and response.status == 200:
                try:
                    body = await response.body()
                    ext = ct.split("/")[-1].split(";")[0].strip()
                    if ext in ("jpeg", "jpg", "png", "webp", "gif"):
                        fname = f"{video_id}_{len(saved)}.{ext}"
                        path = dest_dir / fname
                        path.write_bytes(body)
                        saved.append(path)
                        log.info("Image saved: %s", path)
                except Exception as e:
                    log.warning("Could not save image: %s", e)

        page.on("response", handle_response)

        # Try to navigate to the images section if it exists
        try:
            await page.click('[aria-label*="Image" i], [data-tooltip*="Image" i]', timeout=5_000)
            await asyncio.sleep(2)
        except PlaywrightTimeout:
            pass

        # Scroll to trigger lazy-loaded images
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, 600)")
            await asyncio.sleep(0.8)

        downloaded = list(saved)
        await browser.close()

    return downloaded


async def sync_project(video_id: str, file_type: str = "all") -> list[Path]:
    paths: list[Path] = []
    if file_type in ("video", "all"):
        paths.append(await download_video(video_id))
    if file_type in ("image", "all"):
        paths += await download_images(video_id)
    return paths


def _check_session(page):
    if "accounts.google.com" in page.url:
        raise PermissionError(
            "Session expired. Run 'python login.py' to refresh."
        )


async def _maybe_generate(page) -> None:
    """Click 'Generate video' if present and wait for completion."""
    try:
        btn = page.locator(
            'button:has-text("Genera video"), button:has-text("Generate video"), '
            'button:has-text("Render"), button:has-text("Crea video")'
        )
        if await btn.count() > 0:
            log.info("Generation button found, clicking...")
            await btn.first.click()
            # Wait for the button to disappear or a progress bar to complete
            await page.wait_for_selector(
                '[aria-label*="Download" i], button:has-text("Download")',
                timeout=300_000,  # up to 5 min for long videos
            )
            log.info("Generation complete.")
    except PlaywrightTimeout:
        log.info("No generation button found, proceeding to download.")


async def _click_download_video(page) -> bool:
    """Try multiple strategies to click the Download video button."""

    # Strategy 1: File menu → Download video
    try:
        await page.click(
            'button[aria-label="File"], [data-tooltip="File"], '
            'button:has-text("File")',
            timeout=8_000,
        )
        await asyncio.sleep(0.5)
        await page.click(
            '[role="menuitem"]:has-text("Download"), '
            'li:has-text("Download video"), '
            '[aria-label*="Download video" i]',
            timeout=5_000,
        )
        return True
    except PlaywrightTimeout:
        pass

    # Strategy 2: Direct download button in toolbar
    try:
        await page.click(
            '[aria-label*="Download video" i], [data-tooltip*="Download" i]',
            timeout=8_000,
        )
        return True
    except PlaywrightTimeout:
        pass

    # Strategy 3: Three-dot / More options menu
    try:
        await page.click(
            '[aria-label="More options"], [aria-label="More actions"], '
            '[aria-label="Menu"]',
            timeout=5_000,
        )
        await asyncio.sleep(0.5)
        await page.click('[role="menuitem"]:has-text("Download")', timeout=5_000)
        return True
    except PlaywrightTimeout:
        pass

    return False
