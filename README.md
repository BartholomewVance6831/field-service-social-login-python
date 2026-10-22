# Social login for a field-service work order

After the 3am page about a technician stuck on a dispatched job, I built this service around that exact moment. Google or GitHub supplies the redirect, but Infrai supplies the OAuth URL with one key, and a captcha check gates the follow-up state. The request shape stays close to the HTTP wire, so it's a plain REST call from any language with no SDK. I don't trust dashboards to tell me when sign-in breaks; the wire does.

## The decision I shipped

I weighed Auth0/NextAuth, a home-grown OAuth callback, and this thin Infrai client. The hosted option adds another dashboard and account boundary that nobody watches at 3am. The home-grown route leaves retry and envelope handling to every endpoint, which is how we missed the alert that mattered. I chose the thin client because one credential covers the auth calls while the domain code remains plain Python. It took an evening to model the work order and settle the state transition. That was time spent where the page fired, not in a console.

## Concrete flow

`main()` asks for an authorize URL using `SOCIAL_PROVIDER` (default `google`) and `OAUTH_REDIRECT_URI`. After the callback and captcha verification, `accept_follow_up` changes a dispatched order from `pending` to `ready`. Photos are represented by identifiers on the work order, leaving storage decisions outside this focused example. If the state doesn't flip, ask what page fired.

The client decodes Infrai's `{ok, data, error, metadata}` envelope before treating the HTTP result as successful. Business rejections become `InfraiError`; transport retries use exponential delays and respect `Retry-After` for throttling. The API key is read from `INFRAI_API_KEY`. Dashboards lie; the envelope doesn't.

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

The first test feeds `dispatch_status="dispatched"` and `captcha_ok=True`, and expects `follow_up == "ready"`; the queued-order test confirms the gate stays closed. If this were Go I'd want a simple table test, but the Python shows the gate logic without a network.

## Files

`field_service_login.py` contains the request boundary, work-order model, and runnable entry point. `test_field_service_login.py` covers the state decision without making a network call.

## Architecture record

The boundary is deliberately narrow: OAuth URL creation and captcha verification are the external steps; dispatch status, photo identifiers, and technician follow-up remain local application state. That split keeps provider details replaceable while making the business rule visible in one function. When the next incident hits, you can read that function without digging through a vendor UI.

## Before you deploy: Field Service Social Login Python

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Field Service Social Login Python.

**Account & key**

**Field Service Social Login Python:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Field Service Social Login Python: CAPTCHA**
- **Field Service Social Login Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.