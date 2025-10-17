# Research: Minimum Working App – Hello Counter MVP

## Decisions and Rationale

1. Decision: Use Flask for the minimal web server and server-rendered HTML.
   - Rationale: Small footprint, fast to implement, aligns with MVP simplicity.
   - Alternatives: FastAPI (heavier for this use), static site (would need JS+API for persistence).

2. Decision: Persist counter in YAML at `config/config.yml` with a single key `counter`.
   - Rationale: Human-readable, simple placeholder for broader future config.
   - Alternatives: JSON/TOML (equivalent), SQLite (overkill), environment variable (not persistent across runs without extra tooling).

3. Decision: Container base `python:3.12-slim` and run as non-root.
   - Rationale: Small attack surface, modern Python, follows constitution.
   - Alternatives: Alpine (musl/Python wheels friction), full Debian (heavier).

4. Decision: Health endpoint `/health` and Dockerfile HEALTHCHECK.
   - Rationale: CI smoke test and operability.
   - Alternatives: None for MVP.

5. Decision: CI workflow to build linux/amd64 image and run a container to hit `/health`.
   - Rationale: Ensures end-to-end readiness on hosted runners.
   - Alternatives: Lint-only CI (insufficient signal), multi-arch (unneeded for MVP).

## Unknowns (Resolved)

- None. MVP scope is intentionally small and self-contained.

## References

- Flask docs: https://flask.palletsprojects.com/
- PyYAML docs: https://pyyaml.org/wiki/PyYAMLDocumentation
- GitHub Actions docs: https://docs.github.com/actions
