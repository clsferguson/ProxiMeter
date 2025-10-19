# Data Model for ProxiMeter Streams

Entity: Stream
- id: UUIDv4 (string)
- name: string (1–50 chars, unique case-insensitive)
- rtsp_url: string (must start with rtsp://, non-empty host; may include credentials)
- created_at: string (ISO8601 timestamp)
- order: integer (list ordering; lower first)
- status: enum { Active, Inactive }

Validation rules
- name required; trim; 1–50; unique CI against existing streams
- rtsp_url required; pattern rtsp://host[/...] ; host non-empty
- order maintained contiguous starting at 0 or 1; server normalizes
- status set Active on successful probe; Inactive otherwise

Relationships
- None (flat list in YAML)

State transitions
- On create: validate → probe connectivity → status Active if first frame within timeout, else Inactive
- On edit: same validations; if rtsp_url changed, re-probe
- On delete: remove and renumber orders
- On reorder: update orders atomically according to provided array of ids
