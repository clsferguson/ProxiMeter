# Quickstart: Hello Counter MVP

## Prerequisites
- Docker (with buildx)

## Build
```powershell
# From repo root
$Env:DOCKER_BUILDKIT=1
$tag = "proximeter/hello-counter:dev"
docker build --platform linux/amd64 -t $tag .
```

## Run (with persistent config)
```powershell
# Create a local folder for config persistence
$config = "${PWD}/config"
if (!(Test-Path $config)) { New-Item -ItemType Directory -Path $config | Out-Null }

# Run the container mapping config volume and port 8000
$tag = "proximeter/hello-counter:dev"
docker run --rm -p 8000:8000 -v "$config:/app/config" --name hello-counter $tag
```

Open http://localhost:8000 to view the app. Use the button to increment the counter. Refresh: the value persists.

If port 8000 is already in use, pick another host port, e.g.:
```powershell
docker run --rm -p 8080:8000 -v "$config:/app/config" --name hello-counter $tag
```

## Health check
```powershell
Invoke-WebRequest http://localhost:8000/health
```

## CI expectations
- On PRs and pushes, CI builds the image for linux/amd64 and runs a container to verify `/health`.
	- Health is considered ready when status is 200 and body is `ok`.
