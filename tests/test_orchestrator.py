from constellation.core.orchestrator import Orchestrator
from constellation.core.demo import demo_worker
from constellation.tui.app import ConstellationApp


def test_fork_and_persist(tmp_path):
    database = tmp_path / "state.db"
    first = Orchestrator(database)
    root = first.create_node("Root", "Investigate")
    child = first.fork(root.id, "Tests", "Run tests")
    first.set_state(child.id, "completed")
    first.close()

    second = Orchestrator(database)
    assert [node.title for node in second.list_nodes()] == ["Root", "Tests"]
    assert second.get_node(child.id).state == "completed"
    assert second.tree_lines()[1][1] == "   └─ "


def test_invalid_state_is_rejected(tmp_path):
    orchestrator = Orchestrator(tmp_path / "state.db")
    node = orchestrator.create_node("Root", "Prompt")
    try:
        orchestrator.set_state(node.id, "unknown")
    except ValueError as error:
        assert "Unknown state" in str(error)
    else:
        raise AssertionError("invalid state was accepted")


def test_background_worker_streams_and_completes(tmp_path):
    orchestrator = Orchestrator(tmp_path / "state.db")
    node = orchestrator.create_node("Worker", "Prompt")
    thread = orchestrator.start(node.id, lambda _: ["step one", "step two"])
    thread.join(timeout=2)
    assert orchestrator.get_node(node.id).state == "completed"
    assert [event.message for event in orchestrator.events_for(node.id)][-3:] == [
        "step one", "step two", "Background execution completed"
    ]


def test_demo_worker_produces_mission_signals(tmp_path):
    orchestrator = Orchestrator(tmp_path / "state.db")
    node = orchestrator.create_node("Demo", "Inspect the repository")
    thread = orchestrator.start(node.id, demo_worker)
    thread.join(timeout=4)
    assert orchestrator.get_node(node.id).state == "completed"
    events = orchestrator.events_for(node.id)
    assert len(events) == 7
    assert events[1].message == "Background execution started"
    assert events[-1].message == "Background execution completed"


def test_ui_receives_live_worker_signals(tmp_path):
    import asyncio

    async def check():
        orchestrator = Orchestrator(tmp_path / "ui.db")
        node = orchestrator.create_node("UI", "Watch signals")
        async with ConstellationApp(orchestrator).run_test() as pilot:
            thread = orchestrator.start(node.id, lambda _: ["live signal"])
            await asyncio.to_thread(thread.join, 2)
            await pilot.pause()
            assert "Background execution completed" in str(pilot.app.query_one("#detail").render())
        orchestrator.close()

    asyncio.run(check())
