from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from .orchestrator import Orchestrator
from .repository import Repository
from .schemas import ColonyResult, CreateTask, TaskResponse, TaskStatus

repository = Repository(os.getenv("KOMOREBI_DB", "komorebi.db"))
orchestrator = Orchestrator(repository)
app = FastAPI(title="Komorebi", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/tasks", response_model=TaskResponse, status_code=202)
async def create_task(request: CreateTask) -> TaskResponse:
    task = TaskResponse(id=str(uuid.uuid4()), description=request.description, language=request.language, status=TaskStatus.queued, created_at=datetime.now(timezone.utc))
    repository.create_task(task)
    await orchestrator.events.publish("task.created", task.id)
    asyncio.create_task(orchestrator.run_task(task.id, task.description, request.colonies))
    return task


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str) -> TaskResponse:
    task = repository.get_task(task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return task


@app.get("/api/tasks/{task_id}/colonies", response_model=list[ColonyResult])
def get_colonies(task_id: str) -> list[ColonyResult]:
    if not repository.get_task(task_id):
        raise HTTPException(404, "task not found")
    return repository.colonies(task_id)


@app.get("/api/tasks/{task_id}/result", response_model=ColonyResult)
def get_result(task_id: str) -> ColonyResult:
    task = repository.get_task(task_id)
    if not task:
        raise HTTPException(404, "task not found")
    if not task.winner_id:
        raise HTTPException(409, "result not available")
    return next(item for item in repository.colonies(task_id) if item.id == task.winner_id)


@app.get("/api/tasks/{task_id}/events")
def get_events(task_id: str) -> list[dict]:
    if not repository.get_task(task_id):
        raise HTTPException(404, "task not found")
    return repository.events(task_id)


@app.websocket("/ws/tasks/{task_id}")
async def task_events(websocket: WebSocket, task_id: str) -> None:
    if not repository.get_task(task_id):
        await websocket.close(code=4404)
        return
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()
    orchestrator.events.subscribers[task_id].add(queue)
    try:
        for event in repository.events(task_id):
            await websocket.send_json(event)
        while True:
            event = await queue.get()
            await websocket.send_json(event.model_dump(mode="json"))
    except WebSocketDisconnect:
        pass
    finally:
        orchestrator.events.subscribers[task_id].discard(queue)
