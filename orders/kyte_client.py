from __future__ import annotations

import logging
from typing import Any, Dict, Optional


logger = logging.getLogger(__name__)


class KyteClient:
    """Mock Kyte service client.

    In a real integration, this would perform signed HTTP requests to the Kyte
    backend. For this case exercise, we simply log the outbound event and
    return a mocked response structure so the rest of the app can proceed.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = base_url or "https://mock.kyte"
        self.api_key = api_key or "mock-key"

    def _log(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("KYTE OUTBOUND → %s | payload=%s", event, payload)
        # Return a stable mocked response
        return {"ok": True, "event": event, "echo": payload}

    # Outbound notifications from restaurant → Kyte
    def notify_preparation_accepted(self, order_id: int) -> Dict[str, Any]:
        return self._log("preparation_accepted", {"order_id": order_id})

    def notify_preparation_rejected(self, order_id: int, reason: str) -> Dict[str, Any]:
        return self._log("preparation_rejected", {"order_id": order_id, "reason": reason})

    def notify_preparation_delayed(self, order_id: int, delay_minutes: int, reason: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"order_id": order_id, "delay_minutes": delay_minutes}
        if reason:
            payload["reason"] = reason
        return self._log("preparation_delayed", payload)

    def notify_preparation_cancelled(self, order_id: int, reason: str) -> Dict[str, Any]:
        return self._log("preparation_cancelled", {"order_id": order_id, "reason": reason})

    def notify_preparation_done(self, order_id: int) -> Dict[str, Any]:
        return self._log("preparation_done", {"order_id": order_id})


# Singleton-style helper so viewsets can reuse a shared client
kyte_client = KyteClient()


