# ProxiMeter Makefile
# Build, run, test, and push Docker images

# Configuration
IMAGE_NAME := proximeter/rtsp-streams
IMAGE_TAG := dev
PLATFORM := linux/amd64
APP_PORT := 8000
REGISTRY := ghcr.io/clsferguson
FULL_IMAGE := $(REGISTRY)/proximeter:latest

# Default target
.PHONY: help
help:
	@echo "ProxiMeter - RTSP Stream Manager"
	@echo ""
	@echo "Available targets:"
	@echo "  make build       - Build Docker image (linux/amd64)"
	@echo "  make run         - Run container locally"
	@echo "  make stop        - Stop running container"
	@echo "  make logs        - View container logs"
	@echo "  make test        - Run tests in container"
	@echo "  make shell       - Open shell in running container"
	@echo "  make clean       - Remove container and image"
	@echo "  make push        - Push image to registry"
	@echo "  make health      - Check health endpoint"
	@echo "  make metrics     - View Prometheus metrics"
	@echo "  make dry-run     - Test build with CI_DRY_RUN=true"
	@echo ""
	@echo "Environment variables:"
	@echo "  APP_PORT=$(APP_PORT)"
	@echo "  IMAGE_NAME=$(IMAGE_NAME)"
	@echo "  IMAGE_TAG=$(IMAGE_TAG)"
	@echo "  PLATFORM=$(PLATFORM)"

# Build Docker image with buildx
.PHONY: build
build:
	@echo "Building Docker image for $(PLATFORM)..."
	docker buildx build \
		--platform $(PLATFORM) \
		--tag $(IMAGE_NAME):$(IMAGE_TAG) \
		--load \
		.
	@echo "Build complete: $(IMAGE_NAME):$(IMAGE_TAG)"

# Run container locally
.PHONY: run
run:
	@echo "Starting container on port $(APP_PORT)..."
	docker run -d \
		--name proximeter-rtsp-streams \
		--platform $(PLATFORM) \
		-p $(APP_PORT):$(APP_PORT) \
		-v $(PWD)/config:/app/config \
		-e APP_PORT=$(APP_PORT) \
		-e LOG_LEVEL=INFO \
		--restart unless-stopped \
		$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Container started. Access at http://localhost:$(APP_PORT)"
	@echo "Run 'make logs' to view logs"

# Stop and remove container
.PHONY: stop
stop:
	@echo "Stopping container..."
	-docker stop proximeter-rtsp-streams
	-docker rm proximeter-rtsp-streams
	@echo "Container stopped and removed"

# View container logs
.PHONY: logs
logs:
	docker logs -f proximeter-rtsp-streams

# Run tests (pytest in container)
.PHONY: test
test:
	@echo "Running tests..."
	docker run --rm \
		--platform $(PLATFORM) \
		-v $(PWD)/tests:/app/tests \
		-e CI_DRY_RUN=false \
		$(IMAGE_NAME):$(IMAGE_TAG) \
		sh -c "pip install pytest pytest-asyncio && pytest tests/ -v"

# Open shell in running container
.PHONY: shell
shell:
	docker exec -it proximeter-rtsp-streams /bin/bash

# Clean up container and image
.PHONY: clean
clean: stop
	@echo "Removing image..."
	-docker rmi $(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Cleanup complete"

# Push image to registry
.PHONY: push
push:
	@echo "Tagging image for registry..."
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(FULL_IMAGE)
	@echo "Pushing to $(FULL_IMAGE)..."
	docker push $(FULL_IMAGE)
	@echo "Push complete"

# Check health endpoint
.PHONY: health
health:
	@echo "Checking health endpoint..."
	@curl -s http://localhost:$(APP_PORT)/health | jq . || curl -s http://localhost:$(APP_PORT)/health

# View Prometheus metrics
.PHONY: metrics
metrics:
	@echo "Fetching Prometheus metrics..."
	@curl -s http://localhost:$(APP_PORT)/metrics

# Test build with CI_DRY_RUN
.PHONY: dry-run
dry-run:
	@echo "Testing build with CI_DRY_RUN=true..."
	docker run --rm \
		--platform $(PLATFORM) \
		-e CI_DRY_RUN=true \
		$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Dry run successful - container built and dependencies verified"

# Rebuild and restart (convenience target)
.PHONY: rebuild
rebuild: stop build run
	@echo "Rebuild and restart complete"

# Run with docker-compose
.PHONY: compose-up
compose-up:
	@echo "Starting with docker-compose..."
	docker compose up --build -d
	@echo "Services started. Access at http://localhost:$(APP_PORT)"

# Stop docker-compose
.PHONY: compose-down
compose-down:
	@echo "Stopping docker-compose services..."
	docker compose down
	@echo "Services stopped"

# View docker-compose logs
.PHONY: compose-logs
compose-logs:
	docker compose logs -f
