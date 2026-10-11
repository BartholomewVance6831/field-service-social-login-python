from field_service_login import InfraiClient, WorkOrder, accept_follow_up


def test_captcha_verify_includes_widget_record_id(monkeypatch):
    client = InfraiClient(api_key="test-key")
    captured = {}

    def fake_request(method, path, payload):
        captured.update(payload)
        return {"data": {"valid": True}}

    monkeypatch.setattr(client, "_request", fake_request)
    assert client.verify_captcha("widget-1", "captcha-token", "login") == {"valid": True}
    assert captured == {
        "widget_record_id": "widget-1", "token": "captcha-token", "action": "login"
    }


def test_dispatched_order_becomes_ready_after_captcha():
    order = WorkOrder("WO-42", "tech-7", dispatch_status="dispatched")
    result = accept_follow_up(order, captcha_ok=True)
    assert result.follow_up == "ready"


def test_queued_order_stays_pending():
    order = WorkOrder("WO-43", "tech-7", dispatch_status="queued")
    assert accept_follow_up(order, captcha_ok=True).follow_up == "pending"
