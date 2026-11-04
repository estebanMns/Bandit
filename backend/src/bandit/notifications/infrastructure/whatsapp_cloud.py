"""Adaptador de WhatsApp Business Cloud API con plantilla aprobada."""

import httpx

from bandit.notifications.domain.models import AlertMessage

_TIMEOUT_SECONDS = 15


class WhatsAppCloudSender:
    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        template_name: str,
        template_language: str,
        api_version: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._access_token = access_token
        self._template_name = template_name
        self._template_language = template_language
        self._url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
        self._client = client or httpx.AsyncClient(timeout=_TIMEOUT_SECONDS)

    async def send(self, to: str, message: AlertMessage) -> None:
        if not self._access_token:
            raise RuntimeError("WhatsApp no está configurado")
        parameters = [
            message.establishment,
            message.address,
            message.situation,
            message.time,
            message.description,
        ]
        response = await self._client.post(
            self._url,
            headers={"Authorization": f"Bearer {self._access_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": to.removeprefix("+"),
                "type": "template",
                "template": {
                    "name": self._template_name,
                    "language": {"code": self._template_language},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [{"type": "text", "text": text} for text in parameters],
                        }
                    ],
                },
            },
        )
        response.raise_for_status()
