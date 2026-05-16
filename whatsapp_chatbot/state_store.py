from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any


class MemoryStateStore:
    """Small in-memory store for local use. Replace with Redis/PostgreSQL in production."""

    def __init__(self, session_hours: int) -> None:
        self._lock = Lock()
        self._session_ttl = timedelta(hours=session_hours)
        self._absence_enabled = False
        self._last_customer_message_at: dict[str, datetime] = {}
        self._last_agent_reply_at: dict[str, datetime] = {}
        self._pending_timers: dict[str, Any] = {}

    def set_absence(self, enabled: bool) -> None:
        with self._lock:
            self._absence_enabled = enabled

    def absence_enabled(self) -> bool:
        with self._lock:
            return self._absence_enabled

    def record_customer_message(self, chat_id: str, at: datetime | None = None) -> None:
        with self._lock:
            self._last_customer_message_at[chat_id] = at or datetime.now(timezone.utc)

    def record_agent_reply(self, chat_id: str, at: datetime | None = None) -> None:
        with self._lock:
            self._last_agent_reply_at[chat_id] = at or datetime.now(timezone.utc)

    def can_send_free_text(self, chat_id: str) -> bool:
        with self._lock:
            last_customer_message = self._last_customer_message_at.get(chat_id)
        if not last_customer_message:
            return False
        return datetime.now(timezone.utc) - last_customer_message <= self._session_ttl

    def was_agent_reply_after_last_customer_message(self, chat_id: str) -> bool:
        with self._lock:
            last_customer = self._last_customer_message_at.get(chat_id)
            last_agent = self._last_agent_reply_at.get(chat_id)
        return bool(last_customer and last_agent and last_agent >= last_customer)

    def set_timer(self, chat_id: str, timer: Any) -> None:
        with self._lock:
            old_timer = self._pending_timers.pop(chat_id, None)
            self._pending_timers[chat_id] = timer
        if old_timer:
            old_timer.cancel()

    def pop_timer(self, chat_id: str) -> Any:
        with self._lock:
            return self._pending_timers.pop(chat_id, None)

    def cancel_timer(self, chat_id: str) -> None:
        timer = self.pop_timer(chat_id)
        if timer:
            timer.cancel()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "absence_enabled": self._absence_enabled,
                "last_customer_message_at": {
                    chat_id: value.isoformat() for chat_id, value in self._last_customer_message_at.items()
                },
                "last_agent_reply_at": {
                    chat_id: value.isoformat() for chat_id, value in self._last_agent_reply_at.items()
                },
                "pending_timeouts": list(self._pending_timers.keys()),
            }
