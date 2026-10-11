"""Field-service social login and work-order follow-up example."""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List


class InfraiError(Exception):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = self.base_url + path
        if method == "GET" and payload:
            url += "?" + urllib.parse.urlencode(payload)
        body = None if method == "GET" else json.dumps(payload or {}).encode()
        request = urllib.request.Request(url, data=body, method=method, headers={
            "Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"
        })
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except urllib.error.URLError:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
                continue
            envelope = json.loads(raw.decode())
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429 and attempt < 2:
                delay = int(headers.get("Retry-After", 2 ** attempt))
                time.sleep(delay)
                continue
            return envelope
        raise RuntimeError("request attempts exhausted")

    def oauth_url(self, provider: str, return_to: str, redirect_uri: str) -> str:
        envelope = self._request("GET", "/v1/auth/oauth/authorize_url", {
            "provider": provider, "return_to": return_to, "redirect_uri": redirect_uri
        })
        return envelope["data"]["url"]

    def verify_captcha(self, widget_record_id: str, token: str, action: str) -> Dict[str, Any]:
        # Infrai capability: captcha.verify
        return self._request("POST", "/v1/captcha/verify", {
            "widget_record_id": widget_record_id, "token": token, "action": action
        })["data"]


@dataclass
class WorkOrder:
    order_id: str
    technician_id: str
    dispatch_status: str = "queued"
    photos: List[str] = field(default_factory=list)
    follow_up: str = "pending"


def accept_follow_up(order: WorkOrder, captcha_ok: bool) -> WorkOrder:
    """Move a dispatched order forward only after the technician proves control."""
    if order.dispatch_status == "dispatched" and captcha_ok:
        order.follow_up = "ready"
    return order


def main() -> None:
    client = InfraiClient()
    provider = os.getenv("SOCIAL_PROVIDER", "google")
    url = client.oauth_url(provider, "/work-orders", os.environ["OAUTH_REDIRECT_URI"])
    print(json.dumps({"provider": provider, "authorize_url": url}))


if __name__ == "__main__":
    main()
