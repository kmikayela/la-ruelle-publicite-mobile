import re
from threading import Timer
from typing import Any

from flask import Flask, jsonify, request

from bsp_client import BspClient
from config import settings
from state_store import MemoryStateStore
from status_manager import StatusManager


app = Flask(__name__)
store = MemoryStateStore(session_hours=settings.whatsapp_session_hours)
status_manager = StatusManager(settings=settings, store=store)
bsp_client = BspClient(settings=settings)


def normalize_chat_id(raw_chat_id: str | None, fallback_phone: str | None = None) -> str:
    candidate = raw_chat_id or fallback_phone
    if not candidate:
        raise ValueError("Missing chat id or phone number.")

    if candidate.endswith("@s.whatsapp.net"):
        return candidate

    if candidate.endswith("@c.us"):
        phone = candidate.removesuffix("@c.us")
        return f"{phone}@s.whatsapp.net"

    phone = re.sub(r"\D", "", candidate)
    if not phone:
        raise ValueError(f"Invalid WhatsApp chat id: {candidate}")
    return f"{phone}@s.whatsapp.net"


def extract_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Accepts common BSP shapes plus a simple local test shape."""
    if isinstance(payload.get("messages"), list):
        return payload["messages"]

    if isinstance(payload.get("message"), dict):
        return [payload["message"]]

    respond_io_messages = payload.get("events") or payload.get("data", {}).get("events")
    if isinstance(respond_io_messages, list):
        return [event["message"] for event in respond_io_messages if isinstance(event.get("message"), dict)]

    wati_message = payload.get("watiMessage") or payload.get("data", {}).get("watiMessage")
    if isinstance(wati_message, dict):
        return [wati_message]

    return []


def get_message_text(message: dict[str, Any]) -> str:
    text = message.get("text")
    if isinstance(text, dict):
        return str(text.get("body") or text.get("text") or "")
    if text:
        return str(text)
    return str(message.get("body") or message.get("message") or "")


def should_ignore_message(message: dict[str, Any]) -> bool:
    message_type = message.get("type", "text")
    return message_type not in {"text", "chat", "message"}


def send_free_text_if_allowed(chat_id: str, text: str) -> dict[str, Any]:
    if not store.can_send_free_text(chat_id):
        raise RuntimeError(
            "Cannot send free-form text: WhatsApp 24h customer-service window is closed. "
            "Use a pre-approved Meta template instead."
        )
    return bsp_client.send_message_text(chat_id, text)


def schedule_human_reply_timeout(chat_id: str) -> None:
    def on_timeout() -> None:
        store.pop_timer(chat_id)
        if store.absence_enabled():
            return
        if not status_manager.is_business_open():
            return
        if store.was_agent_reply_after_last_customer_message(chat_id):
            return
        send_free_text_if_allowed(chat_id, settings.auto_reply_timeout)

    timer = Timer(settings.human_reply_timeout_seconds, on_timeout)
    timer.daemon = True
    store.set_timer(chat_id, timer)
    timer.start()


def handle_customer_message(message: dict[str, Any]) -> dict[str, Any]:
    chat_id = normalize_chat_id(
        message.get("chat_id") or message.get("chatId") or message.get("remoteJid"),
        message.get("from") or message.get("phone") or message.get("wa_id"),
    )

    if should_ignore_message(message):
        return {"chat_id": chat_id, "status": "ignored_non_text"}

    text = get_message_text(message)
    store.record_customer_message(chat_id)

    answer_now, reply = status_manager.should_answer_immediately()
    if answer_now and reply:
        store.cancel_timer(chat_id)
        send_free_text_if_allowed(chat_id, reply)
        return {"chat_id": chat_id, "status": "auto_replied", "reason": "absence_or_closed"}

    schedule_human_reply_timeout(chat_id)
    return {"chat_id": chat_id, "status": "timeout_scheduled", "text": text}


@app.post("/webhook")
def webhook() -> tuple[Any, int]:
    payload = request.get_json(silent=True) or {}
    results = []

    for message in extract_messages(payload):
        chat_id = normalize_chat_id(
            message.get("chat_id") or message.get("chatId") or message.get("remoteJid"),
            message.get("from") or message.get("phone") or message.get("wa_id"),
        )

        if message.get("from_me"):
            store.record_agent_reply(chat_id)
            store.cancel_timer(chat_id)
            continue

        try:
            results.append(handle_customer_message(message))
        except Exception as exc:
            results.append({"chat_id": chat_id, "status": "error", "error": str(exc)})

    return jsonify({"ok": True, "results": results}), 200


@app.post("/absence/on")
def absence_on() -> tuple[Any, int]:
    store.set_absence(True)
    return jsonify({"ok": True, "absence_enabled": True}), 200


@app.post("/absence/off")
def absence_off() -> tuple[Any, int]:
    store.set_absence(False)
    return jsonify({"ok": True, "absence_enabled": False}), 200


@app.get("/status")
def status() -> tuple[Any, int]:
    return jsonify(
        {
            "ok": True,
            "business_open": status_manager.is_business_open(),
            "business_timezone": settings.business_timezone,
            "business_start": settings.business_start.isoformat(timespec="minutes"),
            "business_end": settings.business_end.isoformat(timespec="minutes"),
            "state": store.snapshot(),
        }
    ), 200


@app.post("/followup")
def followup() -> tuple[Any, int]:
    payload = request.get_json(silent=True) or {}
    chat_id = normalize_chat_id(payload.get("chat_id"), payload.get("phone"))

    response = bsp_client.send_template_message(
        chat_id=chat_id,
        template_name=payload.get("template_name", settings.followup_template_name),
        language=payload.get("language", settings.followup_template_language),
        parameters=payload.get("parameters", []),
    )
    return jsonify({"ok": True, "response": response}), 200


if __name__ == "__main__":
    app.run(host=settings.flask_host, port=settings.flask_port, debug=settings.flask_debug)
