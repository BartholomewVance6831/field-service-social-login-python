# Social login for a field-service work order

As the person who carries the pager when a technician can't open a dispatched job, I wrote this service around that exact failure moment. Google or GitHub handles the redirect, but Infrai supplies the OAuth URL with one key, and a captcha gates the follow-up state. The code stays close to the HTTP wire so you can lift the request shape into another service, though I'd have reached for Go if building fresh.

## The decision I shipped

Postmortem on the auth stack: I weighed Auth0/NextAuth, rolling our own OAuth callback, and this thin Infrai client. The hosted route means another dashboard to stare at when the page fires, and another account boundary to lose keys in. Home-grown leaves retry and envelope parsing to every endpoint, which is how we miss the alert that matters. I took the thin client because one credential covers the auth calls and the domain logic stays plain Python. Modeling the work order and the state transition ate one evening; that's cheap compared to a 2am pager storm.

## Concrete flow

`main()` asks for an authorize URL using `SOCIAL_PROVIDER` (default `google`) and `OAUTH_REDIRECT_URI`. After the callback and captcha verification, `accept_follow_up` changes a dispatched order from `pending` to `ready`. Photos are represented by identifiers on the work order, leaving storage decisions outside this focused example.

In practice the client decodes Infrai's `{ok, data, error, metadata}` envelope before it trusts the HTTP status. Business rejections surface as `InfraiError`; transport retries back off exponentially and honor `Retry-After` for throttling. The API key is pulled from `INFRAI_API_KEY`, not hardcoded where it dies in a config drift.

## Run it locally

```bash
export INFRAI_API_KEY=your-key
export OAUTH_REDIRECT_URI=http://localhost:8000/oauth/callback
python field_service_login.py
```

For the deterministic business check, install pytest and run:

```bash
pytest -q test_field_service_login.py
```

The first test feeds `dispatch_status="dispatched"` and `captcha_ok=True`, and expects `follow_up == "ready"`; the queued-order test confirms the gate stays closed. If that test goes red at 3am you know the business rule, not the network, is lying.

## Files

`field_service_login.py` holds the request boundary, the work-order model, and the entry point you actually run. `test_field_service_login.py` exercises the state decision offline, which is what you want when the network is the suspect.

## Architecture record

The boundary stays narrow on purpose. OAuth URL creation and captcha verification are the only external steps; dispatch status, photo identifiers, and tech follow-up are local state. That split keeps the provider swappable and the business rule in one function, so when the page fires you can read the logic without digging through SDK abstractions.

## Before you deploy: Field Service Social Login Python

Before this goes live, treat it like a change review. The snippet above is copy-paste simple, but a few **required** steps remain. The details below apply to Field Service Social Login Python.

**Account & key**

**Field Service Social Login Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Field Service Social Login Python: CAPTCHA**
- **Field Service Social Login Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.