from typing import Any

import requests

from config import Settings


class BspClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send_message_text(self, chat_id: str, text: str) -> dict[str, Any]:
        if self.settings.bsp_provider == "mock":
            print(f"[MOCK sendMessageText] to={chat_id} text={text}")
            return {"ok": True, "mock": True, "type": "text", "to": chat_id}

        payload = {
            "channelId": self.settings.bsp_channel_id,
            "chatId": chat_id,
            "message": {"type": "text", "text": text},
        }
        return self._post("/sendMessageText", payload)

    def send_template_message(
        self,
        chat_id: str,
        template_name: str,
        language: str,
        parameters: list[str] | None = None,
    ) -> dict[str, Any]:
        if self.settings.bsp_provider == "mock":
            print(
                "[MOCK sendTemplateMessage] "
                f"to={chat_id} template={template_name} language={language} parameters={parameters or []}"
            )
            return {"ok": True, "mock": True, "type": "template", "to": chat_id}

        payload = {
            "channelId": self.settings.bsp_channel_id,
            "chatId": chat_id,
            "template": {
                "name": template_name,
                "language": language,
                "parameters": parameters or [],
            },
        }
        return self._post("/sendTemplateMessage", payload)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.bsp_base_url or not self.settings.bsp_token:
            raise RuntimeError("BSP_BASE_URL and BSP_TOKEN must be configured for real BSP calls.")

        response = requests.post(
            f"{self.settings.bsp_base_url}{path}",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.settings.bsp_token}",
                "Content-Type": "application/json",
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json() if response.content else {"ok": True}
