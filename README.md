[![CI](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml/badge.svg)](https://github.com/<OWNER>/<REPO>/actions/workflows/ci.yml)

# BeevyApp
A project for art-selling web app and live drawing with friends.


## Deploy on Render

live on beevy.onrender.com (might take a few minutes to boot up)
This repository now includes a Render Blueprint config in `render.yaml`.

Manual Web Service
If you prefer to create the service manually, use:

- Build command: `pip install -r requirements.txt`
- Start command: `python scripts/init_db.py ; gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT app:app`


### Health checks

Render uses `/health` (configured in `render.yaml`) to verify the web service is up.

### Troubleshooting (Render shows Unhealthy)

- Check Render logs for `RuntimeError: SECRET_KEY not set` and confirm `SECRET_KEY` exists in service environment variables.
- Confirm the start command matches `render.yaml` and includes `python scripts/init_db.py` before Gunicorn.
- If deploy succeeds but health fails, open `https://<your-service>.onrender.com/health` and confirm it returns `{"status":"ok"}`.

### Database and disk
- Database isnt persistent because the free plan on render doesnt allow it. The changes on the web application will not go through and after a server reset it will go back to the original form. 