from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
SESSION_PATH = os.getenv("SESSION_PATH", "session.json")
DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloads"))
SCHEDULE_CRON = os.getenv("SCHEDULE_CRON", "0 2 * * *")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
]

VIDS_MIME_TYPE = "application/vnd.google-apps.vids"
GOOGLE_VIDS_URL = "https://vids.google.com"
