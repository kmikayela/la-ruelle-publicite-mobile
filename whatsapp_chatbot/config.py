import os
from dataclasses import dataclass
from datetime import time

from dotenv import load_dotenv


load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _time(name: str, default: str) -> time:
    raw = os.getenv(name, default)
    hour, minute = raw.split(":", 1)
    return time(hour=int(hour), minute=int(minute))


def _days(name: str, default: str) -> set[int]:
    raw = os.getenv(name, default)
    return {int(day.strip()) for day in raw.split(",") if day.strip()}


@dataclass(frozen=True)
class Settings:
    flask_host: str = os.getenv("FLASK_HOST", "0.0.0.0")
    flask_port: int = _int("FLASK_PORT", 5000)
    flask_debug: bool = _bool("FLASK_DEBUG", False)

    business_timezone: str = os.getenv("BUSINESS_TIMEZONE", "Europe/Paris")
    business_days: set[int] = None
    business_start: time = None
    business_end: time = None

    human_reply_timeout_seconds: int = _int("HUMAN_REPLY_TIMEOUT_SECONDS", 300)

    bsp_provider: str = os.getenv("BSP_PROVIDER", "mock")
    bsp_base_url: str = os.getenv("BSP_BASE_URL", "").rstrip("/")
    bsp_token: str = os.getenv("BSP_TOKEN", "")
    bsp_channel_id: str = os.getenv("BSP_CHANNEL_ID", "")

    whatsapp_session_hours: int = _int("WHATSAPP_SESSION_HOURS", 24)
    followup_template_name: str = os.getenv("FOLLOWUP_TEMPLATE_NAME", "customer_followup_fr")
    followup_template_language: str = os.getenv("FOLLOWUP_TEMPLATE_LANGUAGE", "fr")

    auto_reply_after_hours: str = os.getenv(
        "AUTO_REPLY_AFTER_HOURS",
        "Bonjour, merci pour votre message. Nous sommes actuellement fermes. "
        "Nous vous repondrons des notre retour aux horaires d'ouverture.",
    )
    auto_reply_absent: str = os.getenv(
        "AUTO_REPLY_ABSENT",
        "Bonjour, merci pour votre message. Nous sommes momentanement indisponibles. "
        "Nous revenons vers vous des que possible.",
    )
    auto_reply_timeout: str = os.getenv(
        "AUTO_REPLY_TIMEOUT",
        "Bonjour, merci pour votre patience. Nous avons bien recu votre message et revenons vers vous rapidement.",
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "business_days", _days("BUSINESS_DAYS", "0,1,2,3,4"))
        object.__setattr__(self, "business_start", _time("BUSINESS_START", "09:00"))
        object.__setattr__(self, "business_end", _time("BUSINESS_END", "18:00"))


settings = Settings()
