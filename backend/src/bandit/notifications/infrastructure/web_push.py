"""Adaptador de Web Push con VAPID."""

import asyncio
import json

from pywebpush import WebPushException, webpush

from bandit.notifications.domain.models import PushTarget, PushTargetGoneError

_GONE_STATUSES = {404, 410}


class VapidPushSender:
    def __init__(self, private_key: str, subject: str) -> None:
        self._private_key = private_key
        self._subject = subject

    def _send(self, target: PushTarget, payload: str) -> None:
        try:
            webpush(
                subscription_info={
                    "endpoint": target.endpoint,
                    "keys": {"p256dh": target.p256dh, "auth": target.auth},
                },
                data=payload,
                vapid_private_key=self._private_key,
                vapid_claims={"sub": self._subject},
            )
        except WebPushException as error:
            status = error.response.status_code if error.response is not None else None
            if status in _GONE_STATUSES:
                raise PushTargetGoneError from error
            raise

    async def send(self, target: PushTarget, title: str, body: str, url: str) -> None:
        if not self._private_key:
            return
        payload = json.dumps({"title": title, "body": body, "url": url})
        await asyncio.to_thread(self._send, target, payload)
