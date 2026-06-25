# bKash QueueStorm Ticket Sorter

Django + DRF backend that classifies a single customer support message into a structured triage payload (`case_type`, `severity`, `department`, `agent_summary`, `human_review_required`, `confidence`). Classification is rule-based keyword matching — no LLM, no API key. A minimal Flowbite test page at `/demo` lets the team try the endpoint by hand.

## Local Run

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

Then exercise the endpoints:

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/sort-ticket \
  -H "Content-Type: application/json" \
  -d '{"ticket_id":"T-001","channel":"app","locale":"en","message":"I sent 5000 taka to a wrong number this morning, please help me get it back"}'
```

Open `http://127.0.0.1:8000/demo` for the Flowbite test page.

## Deploy on Render

- New Web Service, point it at this repo
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn ticketsort.wsgi --log-file -`
- Required env vars: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=<your-render-domain>`
- Confirm `/health` returns `{"status":"ok"}` on the live URL before submitting

## LLM Usage

No, rule based keyword classification.

## Known Issues

None.