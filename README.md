[![CI](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml/badge.svg)](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml)

# BeevyApp
A project for art-selling web app and live drawing with friends.

> Tip: Replace `<OWNER>/<REPO>` in the badge URL with your GitHub repo path to activate the badge.

## Deploy on Render

This repository now includes a Render Blueprint config in `render.yaml`.

### Option A: Blueprint (recommended)

1. Push this repo to GitHub.
2. In Render, click **New +** -> **Blueprint**.
3. Select this repository.
4. Render will detect `render.yaml` and create the web service.

### Option B: Manual Web Service

If you prefer to create the service manually, use:

- Build command: `pip install -r requirements.txt`
- Start command: `python scripts/init_db.py ; gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:$PORT app:app`

### Required environment variables

- `SECRET_KEY` (required by `app.py`)

The Blueprint auto-generates a `SECRET_KEY` for you.

### Health checks

Render uses `/health` (configured in `render.yaml`) to verify the web service is up.

### Troubleshooting (Render shows Unhealthy)

- Check Render logs for `RuntimeError: SECRET_KEY not set` and confirm `SECRET_KEY` exists in service environment variables.
- Confirm the start command matches `render.yaml` and includes `python scripts/init_db.py` before Gunicorn.
- If deploy succeeds but health fails, open `https://<your-service>.onrender.com/health` and confirm it returns `{"status":"ok"}`.

### Persistent database

The app uses SQLite (`beevy.db`). `render.yaml` attaches a persistent disk at `/var/data`, and startup runs `scripts/init_db.py` which:

- creates missing tables safely (`CREATE TABLE IF NOT EXISTS`)
- keeps DB data on persistent storage (`/var/data/beevy.db`)
- links project-level `beevy.db` to the persistent database path on Render
