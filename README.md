# Komorebi

Komorebi is a research-oriented multi-agent software-engineering prototype. It
compares independent colonies of specialist agents and records the evidence
behind the selected solution.

## MVP included here

- FastAPI task API and WebSocket event stream
- Three isolated colonies: conservative, performance, and security
- Structured planner, coder, tester, and reviewer contracts
- SQLite persistence for tasks, colonies, events, and evaluations
- Deterministic local runner for demos and tests (no LLM credentials needed)
- Weighted scoring with hard disqualification constraints

This is deliberately a safe orchestration baseline. It does **not** execute
generated code on the host or claim to reproduce Sakana's research systems.
Connect an LLM provider and a hardened sandbox before accepting untrusted code.

## Run

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Submit a task:

```bash
curl -X POST http://127.0.0.1:8000/api/tasks \
  -H 'content-type: application/json' \
  -d '{"description":"Create a validated FastAPI health endpoint."}'
```

The response has an `id`. Query `/api/tasks/{id}`, `/api/tasks/{id}/colonies`,
and `/api/tasks/{id}/result`; connect to `/ws/tasks/{id}` for live events.

## Validate

```bash
pytest
```

## Safety boundary

The included local runner produces deterministic evaluation evidence only. A
production runner must use a separate, disposable, non-root sandbox with no
network, CPU/memory/time limits, no host secrets, and no Docker socket.
