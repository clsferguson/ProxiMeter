# Data Model: Hello Counter MVP

## Entities

### Configuration
- File: `/app/config/config.yml`
- Fields:
  - `counter` (integer, default 0, min 0, max 2_147_483_647)

## Validation Rules
- If file missing → create with `counter: 0`.
- If file unreadable or malformed → treat as `counter: 0` and display a warning in UI.
- On increment → if current value >= max → keep at max and display a message.

## State Transitions
- Initial → Loaded (from YAML or default)
- Loaded → Incremented (user clicks button) → Persisted (write YAML)
- Persisted → Loaded (on next request or restart)
