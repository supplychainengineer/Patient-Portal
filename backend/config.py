"""Central configuration. Every external connection is read from environment
variables so the portal runs out of the box in dry-run mode and lights up as
you connect each service. See .env.example and the Settings page."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ---------------------------------------------------------------------------
# Practice identity (used on receipts, forms and emails)
# ---------------------------------------------------------------------------
CLINIC_NAME = os.environ.get("CLINIC_NAME", "Your Clinic Name")
CLINIC_ADDRESS = os.environ.get("CLINIC_ADDRESS", "123 Clinic Street, City")
CLINIC_PHONE = os.environ.get("CLINIC_PHONE", "+1 (000) 000-0000")
CLINIC_EMAIL = os.environ.get("CLINIC_EMAIL", "billing@example.com")

# ---------------------------------------------------------------------------
# MongoDB  >>> CONNECT: set MONGO_URL + DB_NAME <<<
# ---------------------------------------------------------------------------
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "patient_portal")

# ---------------------------------------------------------------------------
# Anthropic (powers all six agents)  >>> CONNECT: set ANTHROPIC_API_KEY <<<
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AGENT_MODEL = os.environ.get("AGENT_MODEL", "claude-opus-4-8")
AGENT_MAX_TOKENS = int(os.environ.get("AGENT_MAX_TOKENS", "16000"))
AGENT_MAX_ITERATIONS = int(os.environ.get("AGENT_MAX_ITERATIONS", "25"))

# ---------------------------------------------------------------------------
# Zoho Sheets  >>> CONNECT: create a Self Client at api-console.zoho.com,
# generate a refresh token with scope ZohoSheet.dataAPI.READ and fill these.
# ZOHO_SHEET_RESOURCE_ID is the id in the sheet URL:
#   https://sheet.zoho.com/sheet/open/<resource_id>
# ---------------------------------------------------------------------------
ZOHO_CLIENT_ID = os.environ.get("ZOHO_CLIENT_ID", "")
ZOHO_CLIENT_SECRET = os.environ.get("ZOHO_CLIENT_SECRET", "")
ZOHO_REFRESH_TOKEN = os.environ.get("ZOHO_REFRESH_TOKEN", "")
ZOHO_SHEET_RESOURCE_ID = os.environ.get("ZOHO_SHEET_RESOURCE_ID", "")
ZOHO_ACCOUNTS_BASE = os.environ.get("ZOHO_ACCOUNTS_BASE", "https://accounts.zoho.com")
ZOHO_SHEET_API_BASE = os.environ.get("ZOHO_SHEET_API_BASE", "https://sheet.zoho.com/api/v2")

# ---------------------------------------------------------------------------
# Email (SMTP — works with Zoho Mail, Gmail, SES...)
# >>> CONNECT: set SMTP_HOST/PORT/USER/PASSWORD and EMAIL_DRY_RUN=false <<<
# While EMAIL_DRY_RUN is true (default) every email is captured in the Outbox
# instead of being sent, so you can test all agents safely.
# ---------------------------------------------------------------------------
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or CLINIC_EMAIL)
EMAIL_DRY_RUN = os.environ.get("EMAIL_DRY_RUN", "true").lower() != "false"

# ---------------------------------------------------------------------------
# Generated document storage (receipt / form PDFs)
# ---------------------------------------------------------------------------
STORAGE_DIR = Path(os.environ.get("STORAGE_DIR", str(ROOT_DIR / "storage")))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")


def connection_status() -> dict:
    """Reported on the Settings page so you can see what's left to connect."""
    smtp_configured = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)
    return {
        "anthropic": {
            "configured": bool(ANTHROPIC_API_KEY),
            "detail": "Agents are live." if ANTHROPIC_API_KEY
            else "Set ANTHROPIC_API_KEY in backend/.env to activate the agents.",
        },
        "zoho_sheets": {
            "configured": bool(ZOHO_CLIENT_ID and ZOHO_CLIENT_SECRET and ZOHO_REFRESH_TOKEN and ZOHO_SHEET_RESOURCE_ID),
            "detail": "Zoho sheet connected." if ZOHO_REFRESH_TOKEN
            else "Set ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN and ZOHO_SHEET_RESOURCE_ID.",
        },
        "email": {
            "configured": smtp_configured,
            "dry_run": EMAIL_DRY_RUN,
            "detail": ("Dry-run mode: emails are captured in the Outbox, not sent. "
                       "Set EMAIL_DRY_RUN=false to send for real.") if EMAIL_DRY_RUN
            else ("SMTP connected — emails send for real." if smtp_configured
                  else "Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD."),
        },
    }
