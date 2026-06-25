# bKash QueueStorm — Ticket Sorter

A small Django + DRF service that reads a single customer support message and returns a structured triage payload: `case_type`, `severity`, `department`, `agent_summary`, `human_review_required`, `confidence`. Classification is rule-based keyword matching — no LLM call, no API key, no GPU dependency. A minimal Flowbite test page at `/demo` lets the team try the endpoint by hand.

Built for the **SUST CSE Carnival 2026 — Codex Community Hackathon / QueueStorm Mock Preliminary Round**.

Production-ready for **Railway (Docker)** and **Render (Procfile)** out of the box. No build step on the front end, no LLM call, no API key, no GPU dependency.

---

## 1. Endpoints

| Method | Path           | Purpose                                                |
|--------|----------------|--------------------------------------------------------|
| GET    | `/health`      | Liveness probe, returns `{"status":"ok"}`              |
| POST   | `/sort-ticket` | Classify one ticket, return structured JSON            |
| GET    | `/demo`        | Flowbite + Tailwind test page (no build step)          |

Response time targets (from spec): `/health` < 10 s, `/sort-ticket` < 30 s. The rule-based classifier responds in a few milliseconds.

### Request

```json
POST /sort-ticket
{
  "ticket_id": "T-001",
  "channel": "app",
  "locale": "en",
  "message": "I sent 5000 taka to a wrong number this morning, please help me get it back"
}
```

`channel` ∈ {`app`, `sms`, `call_center`, `merchant_portal`}, `locale` ∈ {`bn`, `en`, `mixed`}, both optional. `ticket_id` and `message` are required; `message` must be non-blank.

### Response

```json
{
  "ticket_id": "T-001",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports sending 5000 BDT to a wrong recipient and requests recovery.",
  "human_review_required": false,
  "confidence": 0.85
}
```

`human_review_required` is `true` for phishing / social engineering and any `critical` severity case.

### Enums

- **case_type**: `wrong_transfer`, `payment_failed`, `refund_request`, `phishing_or_social_engineering`, `other`
- **severity**: `low`, `medium`, `high`, `critical`
- **department**: `customer_support`, `dispute_resolution`, `payments_ops`, `fraud_risk`

---

## 2. Safety Rule (enforced by tests)

`agent_summary` must never ask the customer to share `PIN`, `OTP`, `password`, `CVV`, or full `card number`. The classifier builds summaries from a fixed set of safe templates and runs a post-render token check; the `SafetyTests` test class asserts this for every public sample case and an adversarial phishing prompt.

---

## 3. Local Run

```bash
git clone <this-repo>
cd ticketsort
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test               # 15 tests, all should pass
python manage.py runserver 0.0.0.0:8000
```

Then exercise the service:

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/sort-ticket \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","channel":"app","locale":"en","message":"I sent 5000 taka to a wrong number this morning, please help me get it back"}'
```

Open `http://127.0.0.1:8000/demo` in a browser to use the Flowbite test form.

---

## 4. Deploy — Railway (Docker, recommended)

The repo ships with a `Dockerfile`, `.dockerignore`, and `railway.json` so a fresh Railway project is one-click deploy.

### 4.1 One-time setup

1. Push the repo to GitHub (public or private).
2. In Railway → **New Project** → **Deploy from GitHub repo** → pick this repo. Railway auto-detects the `railway.json` and uses the Dockerfile builder.
3. In the project, **+ New** → **Database** → **PostgreSQL**. Railway provisions it and injects a `DATABASE_URL` variable into the web service automatically.
4. (Optional) **+ New** → **Service** → **Empty Service** for a Redis/cache if you ever need one. Not required today.

### 4.2 Required environment variables

Set these on the **web service** (not the Postgres service) in the Railway **Variables** tab. `DATABASE_URL` is auto-injected when you attach the Postgres plugin, so you do not set it manually.

| Variable | Required | Example / default | Purpose |
|----------|----------|-------------------|---------|
| `SECRET_KEY` | yes | `django-insecure-...` → replace with a long random string | Django signing key |
| `DEBUG` | recommended | `False` | Must be `False` in production |
| `DATABASE_URL` | yes (Railway injects it) | `postgresql://user:pass@host:port/railway` | Database connection |
| `ALLOWED_HOSTS` | yes | `ticketsort-production.up.railway.app` (your service domain) | Django host header check |
| `CSRF_TRUSTED_ORIGINS` | yes | `https://ticketsort-production.up.railway.app` | CSRF safe origins |
| `PORT` | no | `8000` (Railway injects its own) | Bind port |
| `GUNICORN_WORKERS` | no | `3` | Worker count |
| `GUNICORN_TIMEOUT` | no | `60` | Request timeout (seconds) |

The defaults baked into `settings.py` already include `.railway.app` and `.up.railway.app`, so a freshly generated `*.up.railway.app` domain works without changes to `ALLOWED_HOSTS` once `DEBUG=False`.

Generate a strong `SECRET_KEY` locally with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 4.3 What happens at build time

The `Dockerfile` does this in order:

1. `FROM python:3.12-slim` (small, official Python image).
2. Installs system build deps (`build-essential`, `libpq-dev` for `psycopg`, `curl` for the healthcheck).
3. `pip install -r requirements.txt` (separate Docker layer for cache reuse).
4. Copies project, runs `python manage.py collectstatic --noinput` so WhiteNoise has all admin + app static files ready.
5. Creates a non-root `app` user (UID 1000) and `chown`s `/app`.
6. `HEALTHCHECK` calls `curl -fsS http://127.0.0.1:${PORT}/health` every 30 s.

### 4.4 What happens at runtime

The container entrypoint (set in `Dockerfile`, also mirrored in `railway.json`) runs:

```bash
python manage.py migrate --noinput
gunicorn ticketsort.wsgi --bind 0.0.0.0:${PORT} --workers ${GUNICORN_WORKERS:-3} --timeout ${GUNICORN_TIMEOUT:-60} --access-logfile - --error-logfile -
```

`migrate` creates the default Django tables on first boot. `gunicorn` binds to whatever port Railway injects. Railway's `/health` healthcheck reuses the same endpoint every 30 s.

### 4.5 Smoke test after deploy

```bash
SERVICE=https://ticketsort-production.up.railway.app
curl -s $SERVICE/health
# {"status":"ok"}

curl -s -X POST $SERVICE/sort-ticket \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","message":"I sent 3000 to wrong number"}'
# {"ticket_id":"T-001","case_type":"wrong_transfer","severity":"high","department":"dispute_resolution",...}
```

---

## 5. Deploy — Render (alternative)

The repo still ships a `Procfile` so Render works without Docker.

1. Push the repo to GitHub.
2. Render → **New** → **Web Service** → connect the repo.
3. Settings:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn ticketsort.wsgi --log-file -`
   - **Instance type**: Free
4. **Environment variables** (set in Render dashboard, never committed):
   - `SECRET_KEY` — a long random string
   - `DEBUG` — `False`
   - `ALLOWED_HOSTS` — your Render domain, e.g. `ticketsort-xxxx.onrender.com`
5. Deploy. Confirm with:

```bash
curl https://<your-service>.onrender.com/health
# -> {"status":"ok"}
```

### Other platforms

- **Fly.io**: same `Procfile` works. Set `SECRET_KEY`, `DEBUG=False`, and `ALLOWED_HOSTS=<your-app>.fly.dev` as secrets.
- **EC2 / Poridhi Lab / any VPS**: clone, `pip install -r requirements.txt`, run `gunicorn ticketsort.wsgi --bind 0.0.0.0:8000 --log-file -` behind nginx + TLS.

---

## 6. Project Layout

```
ticketsort/
├── manage.py
├── ticketsort/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── tickets/
│   ├── __init__.py
│   ├── apps.py
│   ├── admin.py
│   ├── models.py
│   ├── classifier.py        # rule-based keyword classification
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── tests.py             # 15 tests, including safety rule
│   └── templates/
│       └── tickets/
│           └── demo.html    # Flowbite + Tailwind test page (CDN, no build)
├── requirements.txt
├── Procfile              # Render / Fly start command
├── Dockerfile            # Railway / any container platform
├── .dockerignore
├── railway.json          # Railway service config (DOCKERFILE builder)
├── .env.example
├── .gitignore
└── README.md
```

No custom Django models, no migrations beyond the framework defaults, no external services. SQLite is the default database when `DATABASE_URL` is unset (local dev). Production uses PostgreSQL via `dj-database-url` + `psycopg`, configured by setting `DATABASE_URL` (Railway injects this automatically when you attach a Postgres plugin).

---

## 7. How Classification Works

`classifier.py` lower-cases the message and runs ordered keyword checks. The first match wins; `other` is the catch-all.

1. **phishing_or_social_engineering** → `severity: critical`, `department: fraud_risk`, `human_review_required: true`. Checked first because of stakes.
2. **wrong_transfer** → `severity: high`, `department: dispute_resolution`.
3. **payment_failed** → `severity: high` if a deduction keyword (`deducted`, `money gone`, `balance gone`, `charged twice`) is also present, otherwise `medium`. `department: payments_ops`.
4. **refund_request** → `severity: high` + `department: dispute_resolution` if a dispute keyword (`unauthorized`, `did not authorize`, `i did not make this`, `fraudulent charge`) is also present, otherwise `severity: low` + `department: customer_support`.
5. **other** → `severity: low`, `department: customer_support`.

Confidence rises with the number of matching keywords (0.75–0.9 in the spec range).

`agent_summary` uses a fixed safe template per case type and, when present, includes the amount + currency detected in the message (e.g. `5000 BDT`, `200 USD`). If the rendered text would contain a forbidden token, the renderer falls back to a token-free sentence.

---

## 8. Spec Compliance Checklist

- [x] `GET /health` returns `{"status":"ok"}`
- [x] `POST /sort-ticket` accepts spec request shape, returns spec response shape
- [x] `ticket_id` echoed back exactly
- [x] `case_type` / `severity` / `department` enums match spec
- [x] `human_review_required` set for phishing / critical cases
- [x] `agent_summary` never asks for PIN / OTP / password / CVV / card number
- [x] Public sample cases (1–5) all classify as expected
- [x] No GPU, no LLM, no API key, no secrets in repo
- [x] HTTPS-ready (deploy behind any TLS-terminating host)
- [x] Public runbook in this README

---

## 9. Submission Answers

- **LLM used**: No, rule based keyword classification.
- **Deployment platform**: Render (the included `Procfile` and `runtime.txt` also work on Railway, Fly, or any gunicorn host).
- **Known issues / blockers**: None at submission time.

---

## 10. Local Deployment Replication Runbook (for graders)

To reproduce a working local deployment from a clean checkout:

```bash
# 1. Clone
git clone <repo-url>
cd ticketsort

# 2. Python 3.12 + venv
python3.12 -m venv venv
source venv/bin/activate

# 3. Install
pip install -r requirements.txt

# 4. DB + tests
python manage.py migrate
python manage.py test          # expect: Ran 15 tests ... OK

# 5. Copy env template and edit values
cp .env.example .env
# Set SECRET_KEY to a random string, DEBUG=False for production-like runs

# 6. Run via gunicorn (production-like)
gunicorn ticketsort.wsgi --bind 0.0.0.0:8000 --log-file -

# 7. Smoke test
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/sort-ticket \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","message":"I sent 3000 to wrong number"}'
```

Expected `/sort-ticket` response:

```json
{
  "ticket_id": "T-001",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports sending 3000 BDT to a wrong recipient and requests recovery.",
  "human_review_required": false,
  "confidence": 0.8
}
```