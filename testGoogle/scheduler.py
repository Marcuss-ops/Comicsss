import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from config import SCHEDULE_CRON

log = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _sync_all():
    from playwright_client import list_projects, download_video

    log.info("Scheduled sync started at %s", datetime.now().isoformat())
    projects = await list_projects()
    downloaded = 0

    for project in projects:
        try:
            path = await download_video(project["id"])
            log.info("Downloaded: %s -> %s", project.get("name"), path)
            downloaded += 1
        except Exception as e:
            log.error("Error syncing project %s: %s", project.get("name"), e)

    log.info("Scheduled sync complete. Downloaded %d files.", downloaded)


def start(custom_cron: str | None = None):
    cron = custom_cron or SCHEDULE_CRON
    parts = cron.split()
    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
    )
    scheduler.add_job(_sync_all, trigger, id="sync_all", replace_existing=True)
    scheduler.start()
    log.info("Scheduler started with cron: %s", cron)


def stop():
    scheduler.shutdown(wait=False)
