from datetime import datetime
from zoneinfo import ZoneInfo

from config import Settings
from state_store import MemoryStateStore


class StatusManager:
    def __init__(self, settings: Settings, store: MemoryStateStore) -> None:
        self.settings = settings
        self.store = store

    def now_local(self) -> datetime:
        return datetime.now(ZoneInfo(self.settings.business_timezone))

    def is_business_open(self, moment: datetime | None = None) -> bool:
        current = moment or self.now_local()
        if current.weekday() not in self.settings.business_days:
            return False
        current_time = current.time()
        return self.settings.business_start <= current_time < self.settings.business_end

    def should_answer_immediately(self) -> tuple[bool, str | None]:
        if self.store.absence_enabled():
            return True, self.settings.auto_reply_absent
        if not self.is_business_open():
            return True, self.settings.auto_reply_after_hours
        return False, None
