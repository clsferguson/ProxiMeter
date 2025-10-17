# ProxiMeter — Hello Counter MVP

A minimal Flask web app that shows a Hello page with a persistent counter. Click the button to increment; the value persists to `config/config.yml`.

- Tech: Python 3.12, Flask, Jinja2, PyYAML, Gunicorn
- Endpoints: `/` (UI), `/api/counter` (GET/POST), `/health` (readiness)
- Notes: Meant for LAN-only demos; no authentication. Do not expose publicly without hardening.

## Run with Docker (recommended)

PowerShell (Windows):

```powershell
# From repo root
$Env:DOCKER_BUILDKIT=1
$tag = "proximeter/hello-counter:dev"
docker build --platform linux/amd64 -t $tag .

# Create a local folder for persistent config
$config = "${PWD}/config"
if (!(Test-Path $config)) { New-Item -ItemType Directory -Path $config | Out-Null }

# Run the container mapping config volume and port 8000
$Env:CI_DRY_RUN=$null

docker run --rm -p 8000:8000 -v "$config:/app/config" --name hello-counter $tag
```

Open http://localhost:8000 to view the app.

Health check:

```powershell
Invoke-WebRequest http://localhost:8000/health
```

If port 8000 is in use, map a different host port, e.g. `-p 8080:8000`.

## Development

Project layout:

```
src/app/
  __init__.py      # Flask app factory
  routes.py        # UI + API routes (/, /api/counter, /health)
  config_io.py     # YAML persistence at config/config.yml
  static/styles.css
  templates/index.html
config/config.yml  # Created on first run; mounted via Docker volume
```

Install deps locally (optional):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run via Gunicorn (production-like):

```powershell
# Ensure config folder exists
if (!(Test-Path 'config')) { New-Item -ItemType Directory -Path 'config' | Out-Null }
$env:PYTHONPATH = "$PWD"
gunicorn -w 2 -b 127.0.0.1:8000 src.app.wsgi:app
```

## CI

GitHub Actions builds the linux/amd64 Docker image and performs a smoke test hitting `/health` until it returns `200 ok` (30s timeout).

## Safety

- LAN-only demo posture; no auth or TLS. Do not expose to the internet.
- Writes only within `/app/config/config.yml`.
- Brief mention: a `/metrics` endpoint may be added later to expose Prometheus metrics as the project evolves.

## License

MIT © 2025 clsferguson
