# Feature Specification: Minimum Working App – Hello Counter MVP

**Feature Branch**: `001-flask-hello-counter`  
**Created**: 2025-10-17  
**Status**: Draft  
**Input**: User description: "I want to start with the creation of a minimum working application. I want to have the project working. Lets get the flask webserver up and running in the docker image. create a placeholder readme. MIT licence. The web UI can just be a hello world landing page, (dark theme, purple highlights) with a button and counter. store the counter value in the config.yml as a placeholder. so when the page is closed and opened the number persists."

## User Scenarios & Testing (mandatory)

### User Story 1 - See and increment counter (Priority: P1)

A user opens the landing page, sees a "Hello" message styled with a dark theme and purple highlights, sees the current counter value, and clicks a button to increment the counter. The value updates immediately and remains the same after reloading or revisiting the page.

Why this priority: Delivers the core MVP value: a working UI and persistent state demonstrating end‑to‑end app readiness.

Independent Test: Load the page, click the increment button, refresh the page; the counter value remains incremented.

Acceptance Scenarios:

1. Given no existing configuration file, When the user first loads the page, Then the counter is shown as 0 and a configuration file is created with that value.
2. Given a visible counter value X, When the user clicks the increment button once, Then the counter displays X+1 and the stored value is updated immediately.
3. Given the counter value was updated, When the user refreshes the page or closes and reopens the browser, Then the counter still shows the updated value.

---

### User Story 2 - Run the app in a container (Priority: P2)

An operator builds and runs the application in a container and can access the landing page in a browser. A health endpoint confirms the service is running.

Why this priority: Ensures the application is operational in its intended packaging and easily verifiable.

Independent Test: Build the container image, run it locally, visit the landing page and the health endpoint.

Acceptance Scenarios:

1. Given the repository, When following the README steps, Then an image builds successfully and a container runs serving the landing page.
2. Given a running container, When requesting GET /health, Then the response is HTTP 200 with a simple body (e.g., "ok").

---

### User Story 3 - Repository housekeeping (Priority: P3)

A contributor finds a placeholder README with usage instructions and a permissive license in the repository root.

Why this priority: Improves contributor experience and clarifies legal use from day one.

Independent Test: Verify the presence and contents of the README and license file.

Acceptance Scenarios:

1. Given the repository, When opening the README, Then it explains what the project is and how to build/run the container locally.
2. Given the repository, When opening the license file, Then it contains the full MIT License text with the correct copyright line.

---

### Edge Cases

- Config file missing: created on first read with default counter 0. UI displays: "Using default configuration (counter = 0)."
- Config file unreadable or malformed: reset only the counter key to a safe default (0) and continue; UI displays: "Configuration could not be read; using safe default (0)."
- Write failure (filesystem permissions or read‑only): page shows current in‑memory value and a visible error message; no crash. UI displays: "Could not save counter; running in read‑only mode."
- Concurrent increments (multiple rapid clicks or multiple sessions): increments are applied sequentially and persisted; the displayed value reflects the latest successful write.
- Very large counter values: application prevents overflow by capping at a reasonable maximum (2,147,483,647); shows a message if max reached: "Maximum counter value reached."

## Requirements (mandatory)

### Functional Requirements

- FR-001: Provide a simple landing page with a dark theme and purple highlights that greets the user and displays the current counter value.
	- UI elements: Title text "Hello"; a counter label rendered as "Counter: <value>"; and a button labeled "Increment".
	- Theme tokens: background #121212, primary text #EAEAEA, accent purple #7C3AED. Text-to-background contrast ratios must be ≥ 4.5:1 (WCAG 2.1 AA).
	- Focus visibility: All interactive elements must show a visible 2px outline using the accent color (#7C3AED) when focused.
- FR-002: Provide a single button that increments the counter and updates the displayed value immediately (≤ 200 ms on a typical local machine).
- FR-003: Persist the counter value in a human‑readable YAML configuration file at `/app/config/config.yml`. If the file does not exist, create it with `counter: 0` on first run.
	- Schema: key `counter` (integer ≥ 0; default 0; maximum 2,147,483,647).
- FR-004: The stored counter value must persist across page reloads and application restarts.
	- Container persistence: Across container restarts, persistence is retained only when `/app/config` is bound to a host volume; without a host volume, persistence across restarts is not guaranteed.
	- Read-only or missing config directory: If `/app/config` is missing or mounted read-only, the application must continue to serve the page, display the in-memory value, and show a user-visible error message; no crash.
- FR-005: Expose a simple health endpoint at `/health` that returns HTTP 200 with body `ok` (Content-Type: text/plain) when the service is ready to serve requests. "Ready" means the web server is accepting connections and configuration has been loaded or initialized with defaults.
- FR-006: Package the application to run inside a container image and document build/run steps in the README, including how to map a host volume for `config.yml` persistence.
- FR-007: Include a top‑level `README.md` describing the project purpose, how to build/run locally (including container usage), and the persistence behavior.
- FR-008: Include a top‑level `LICENSE` file with the MIT License text and correct copyright holder and year.
- FR-009: Do not require authentication or external services for this MVP.
- FR-010: Keep all specification and UI language neutral and accessible; avoid implementation‑specific details in user‑facing documentation.

#### Non-Functional Requirements

- NFR-001 (Accessibility): Keyboard navigation must allow focusing and activating the increment button via keyboard (e.g., Tab/Enter/Space). Focus states must be visible (see FR‑001 focus visibility). Color contrast for text and interactive elements must meet WCAG 2.1 AA (≥ 4.5:1 for normal text).
- NFR-002 (Performance): UI update on increment should be ≤ 200 ms (see FR‑002). Initial page load should allow reading and incrementing within 2 seconds (see SC‑001). Health endpoint should respond < 200 ms when ready (see SC‑004).
- NFR-003 (Security posture): Container must run as non‑root. No authentication; intended for LAN‑only usage in MVP. README must note LAN‑only/no‑auth posture explicitly.
- NFR-004 (Observability): Structured logging and metrics are intentionally excluded for this MVP. Minimal user‑visible messages are required for configuration errors (see Edge Cases). Future features may add observability.

#### CI/CD (GitHub Actions) Requirements

- FR-011: Provide a continuous integration workflow that runs automatically on pull requests and pushes to the default branch and performs: (a) container image build for linux/amd64, and (b) a smoke test that runs the container and verifies readiness via an HTTP GET to `/health`.
- FR-012: The CI workflow must not require GPUs or external services; it must execute successfully on standard hosted runners.
- FR-013: The CI workflow must fail if the container fails to build, fails to start, or `/health` does not return HTTP 200 with body `ok` within 30 seconds of container startup.
- FR-014: The CI workflow must report status on pull requests and expose basic logs sufficient to diagnose typical build/startup failures.

### Key Entities (data)

- Configuration: YAML file with a single key `counter` (integer ≥ 0). Additional keys may be added in future versions.

## Success Criteria (mandatory)

### Measurable Outcomes

- SC-001: From first page load, a user can read and increment the counter and see the new value persist after a reload within 2 seconds.
- SC-002: On a clean start with no existing config file, the application creates `config.yml` containing `counter: 0` within 1 second of first request.
- SC-003: After incrementing the counter and restarting the application (or container), the first page load shows the last stored value 100% of the time under normal local conditions.
- SC-004: Health endpoint responds with HTTP 200 in under 200 ms on a local machine when the service is ready.
- SC-005: A new contributor can follow the README to build and run the container locally in under 10 minutes without prior project knowledge.
- SC-006: On pushes and pull requests to the default branch, the CI workflow runs automatically and completes in ≤ 5 minutes under typical hosted runner conditions.
- SC-007: The CI smoke test fails if `/health` is not reachable or does not return HTTP 200 within 30 seconds of container startup.
- SC-008: The CI workflow builds a linux/amd64 image successfully on standard hosted runners without GPU access for 100% of runs under normal conditions.

## Operational Considerations

- Port binding: Default host binding is 8000. If port 8000 is already in use, documentation must indicate selecting an alternate host port (e.g., `-p 8080:8000`).

## Traceability Map (User Stories ↔ FR/SC)

| User Story / Scenario | Related FR | Related SC |
|-----------------------|-----------:|-----------:|
| US1: First load shows 0 and creates config | FR-001, FR-003 | SC-001, SC-002 |
| US1: Increment updates immediately and persists | FR-002, FR-003, FR-004 | SC-001, SC-003 |
| US2: Health endpoint readiness | FR-005 | SC-004 |
| US2: Container build/run and mapping volume | FR-006, FR-007 | SC-005 |
| CI: Build amd64 and smoke test `/health` | FR-011–FR-014 | SC-006–SC-008 |