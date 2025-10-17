# ProxiMeter — Hello Counter MVP

A minimal Flask web app that shows a Hello page with a persistent counter. Click the button to increment; the value persists to `config/config.yml`.

- Tech: Python 3.12, Flask, Jinja2, PyYAML, Gunicorn
- Endpoints: `/` (UI), `/api/counter` (GET/POST), `/health` (readiness)
- Notes: Meant for LAN-only demos; no authentication. Do not expose publicly without hardening.

## Run with Docker (recommended)

```bash
# From repo root
docker compose up --build
```

Open http://localhost:8000 to view the app.

Health check:

```bash
curl http://localhost:8000/health
```

To stop:

```bash
docker compose down
```

If port 8000 is in use, edit `docker-compose.yml` and change the ports mapping (e.g., `8080:8000`).

## Project Structure

```
src/app/
  __init__.py      # Flask app factory
  routes.py        # UI + API routes (/, /api/counter, /health)
  config_io.py     # YAML persistence at config/config.yml
  static/styles.css
  templates/index.html
config/config.yml  # Created on first run; mounted via Docker volume
```

## CI/CD

GitHub Actions builds the linux/amd64 Docker image, performs a smoke test hitting `/health` until it returns `200 ok` (30s timeout), and publishes the image to GitHub Container Registry (ghcr.io).

Pull the latest published image:

```bash
docker pull ghcr.io/clsferguson/proximeter:latest
```

## Safety

- LAN-only demo posture; no auth or TLS. Do not expose to the internet.
- Writes only within `/app/config/config.yml`.
- Brief mention: a `/metrics` endpoint may be added later to expose Prometheus metrics as the project evolves.

## License

MIT © 2025 clsferguson
