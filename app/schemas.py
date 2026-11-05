from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Strategy(str, Enum):
    conservative = "conservative"
    performance = "performance"
    security = "security"


class CreateTask(BaseModel):
    description: str = Field(min_length=8, max_length=12_000)
    language: str = Field(default="python", pattern="^(python)$")
    colonies: int = Field(default=3, ge=1, le=3)
    token_budget: int = Field(default=12_000, ge=1_000, le=100_000)


class Event(BaseModel):
    type: str
    timestamp: datetime
    task_id: str
    colony_id: str | None = None
    agent: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class Metrics(BaseModel):
    correctness: float = Field(ge=0, le=100)
    test_quality: float = Field(ge=0, le=100)
    code_quality: float = Field(ge=0, le=100)
    security: float = Field(ge=0, le=100)
    efficiency: float = Field(ge=0, le=100)
    resource_cost: float = Field(ge=0, le=100)


class Evaluation(BaseModel):
    metrics: Metrics
    score: float
    eligible: bool
    disqualifiers: list[str] = Field(default_factory=list)


class ColonyResult(BaseModel):
    id: str
    strategy: Strategy
    status: TaskStatus
    evaluation: Evaluation | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    id: str
    description: str
    language: str
    status: TaskStatus
    created_at: datetime
    winner_id: str | None = None
