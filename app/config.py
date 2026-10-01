import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = os.getenv("APP_NAME", "ForecastIQ")
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATASETS_DIR = DATA_DIR / "datasets"
REPORTS_DIR = DATA_DIR / "reports"
BRAND_DIR = DATA_DIR / "brand"
DB_PATH = DATA_DIR / "forecast.db"
STATIC_DIR = BASE_DIR / "static"
SAMPLE_DIR = BASE_DIR / "sample_data"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

DEMO_MODE = os.getenv("DEMO_MODE", "1") != "0"
DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@forecastiq.app")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo1234")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "").strip()

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "reports@forecastiq.local")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "").strip()
CONTACT_WHATSAPP = os.getenv("CONTACT_WHATSAPP", "").strip()
MAX_UPLOAD_MB = 40

for d in (DATASETS_DIR, REPORTS_DIR, BRAND_DIR):
    d.mkdir(parents=True, exist_ok=True)
