from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from .repository import Repository
from .schemas import ColonyResult, Event, Metrics, Strategy, TaskStatus
from .scoring import evaluate

AGENTS = ("planner", "coder", "tester", "reviewer")
PROFILES = {
    Strategy.conservative: Metrics(correctness=91, test_quality=88, code_quality=87, security=84, efficiency=78, resource_cost=82),
    Strategy.performance: Metrics(correctness=88, test_quality=80, code_quality=84, security=78, efficiency=94, resource_cost=90),
    Strategy.security: Metrics(correctness=90, test_quality=86, code_quality=85, security=96, efficiency=80, resource_cost=79),
}


class EventBus:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository
        self.subscribers: dict[str, set[asyncio.Queue[Event]]] = defaultdict(set)

    async def publish(self, event_type: str, task_id: str, **kwargs: object) -> None:
        event = Event(type=event_type, timestamp=datetime.now(timezone.utc), task_id=task_id, **kwargs)
        self.repository.append_event(event)
        for queue in self.subscribers[task_id].copy():
            queue.put_nowait(event)


class Orchestrator:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository
        self.events = EventBus(repository)

    async def run_task(self, task_id: str, description: str, colonies: int) -> None:
        self.repository.update_task(task_id, TaskStatus.running)
        await self.events.publish("task.started", task_id)
        strategies = list(Strategy)[:colonies]
        results = await asyncio.gather(*(self._run_colony(task_id, description, strategy) for strategy in strategies))
        eligible = [result for result in results if result.evaluation and result.evaluation.eligible]
        winner = max(eligible, key=lambda item: item.evaluation.score) if eligible else None
        self.repository.update_task(task_id, TaskStatus.completed, winner.id if winner else None)
        await self.events.publish("winner.selected", task_id, colony_id=winner.id if winner else None, payload={"reason": "highest eligible weighted score" if winner else "no eligible colony"})
        await self.events.publish("task.completed", task_id)

    async def _run_colony(self, task_id: str, description: str, strategy: Strategy) -> ColonyResult:
        colony_id = str(uuid.uuid4())
        pending = ColonyResult(id=colony_id, strategy=strategy, status=TaskStatus.running)
        self.repository.upsert_colony(pending, task_id)
        await self.events.publish("colony.started", task_id, colony_id=colony_id, payload={"strategy": strategy.value})
        artifacts: dict[str, str] = {}
        for agent in AGENTS:
            await self.events.publish("agent.started", task_id, colony_id=colony_id, agent=agent)
            await asyncio.sleep(0)  # cooperative scheduling; provider calls plug in here
            artifacts[f"{agent}.md"] = self._artifact(agent, description, strategy)
            await self.events.publish("agent.completed", task_id, colony_id=colony_id, agent=agent)
        metrics = PROFILES[strategy]
        evaluation = evaluate(metrics, mandatory_tests_pass=True, critical_findings=0)
        result = ColonyResult(id=colony_id, strategy=strategy, status=TaskStatus.completed, evaluation=evaluation, artifacts=artifacts)
        self.repository.upsert_colony(result, task_id)
        await self.events.publish("colony.evaluated", task_id, colony_id=colony_id, payload=evaluation.model_dump())
        return result

    @staticmethod
    def _artifact(agent: str, description: str, strategy: Strategy) -> str:
        return f"# {agent.title()} report\n\nTask: {description}\n\nStrategy: {strategy.value}\n\nLocal deterministic baseline; replace with a structured provider response before production use.\n"
