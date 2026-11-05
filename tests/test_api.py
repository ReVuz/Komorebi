import asyncio


def test_task_lifecycle(tmp_path, monkeypatch):
    # Isolate persistence and exercise the API handler with its real background task.
    monkeypatch.setenv("KOMOREBI_DB", str(tmp_path / "startup.db"))
    from app import main
    from app.orchestrator import Orchestrator
    from app.repository import Repository

    repository = Repository(str(tmp_path / "test.db"))
    main.repository = repository
    main.orchestrator = Orchestrator(repository)
    async def submit_and_wait():
        task = await main.create_task(main.CreateTask(description="Implement a small, validated Python endpoint."))
        for _ in range(20):
            if repository.get_task(task.id).status.value == "completed":
                break
            await asyncio.sleep(0)
        return task.id

    task_id = asyncio.run(submit_and_wait())
    assert repository.get_task(task_id).status.value == "completed"
    colonies = [item.model_dump() for item in repository.colonies(task_id)]
    assert len(colonies) == 3
    assert all(colony["evaluation"]["eligible"] for colony in colonies)
    assert main.get_result(task_id).strategy.value == "security"
