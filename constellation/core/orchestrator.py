"""Persistent, thread-safe orchestration tree."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


STATES = ("pending", "running", "completed", "needs-input", "parked", "failed")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(slots=True)
class Event:
    node_id: str
    message: str
    kind: str = "info"
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class AgentNode:
    id: str
    title: str
    prompt: str
    state: str = "pending"
    parent_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


class Orchestrator:
    """Owns graph mutations and persistence; execution is supplied by a callback."""

    def __init__(self, database: str | Path = ".constellation/state.db") -> None:
        self.database = Path(database).expanduser()
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._listeners: list[Callable[[Event], None]] = []
        self._connection = sqlite3.connect(self.database, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, prompt TEXT NOT NULL,
                state TEXT NOT NULL, parent_id TEXT REFERENCES nodes(id),
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT NOT NULL,
                message TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL
            );
        """)
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def subscribe(self, listener: Callable[[Event], None]) -> None:
        self._listeners.append(listener)

    def _emit(self, event: Event) -> None:
        self._connection.execute(
            "INSERT INTO events(node_id,message,kind,created_at) VALUES (?,?,?,?)",
            (event.node_id, event.message, event.kind, event.created_at),
        )
        self._connection.commit()
        for listener in tuple(self._listeners):
            listener(event)

    def create_node(self, title: str, prompt: str, parent_id: str | None = None) -> AgentNode:
        if parent_id and self.get_node(parent_id) is None:
            raise ValueError(f"Parent node does not exist: {parent_id}")
        node = AgentNode(str(uuid.uuid4())[:8], title, prompt, parent_id=parent_id)
        with self._lock:
            self._connection.execute(
                "INSERT INTO nodes VALUES (?,?,?,?,?,?,?)",
                tuple(asdict(node).values()),
            )
            self._connection.commit()
            self._emit(Event(node.id, f"Created branch: {node.title}", "created"))
        return node

    def get_node(self, node_id: str) -> AgentNode | None:
        row = self._connection.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return AgentNode(**dict(row)) if row else None

    def list_nodes(self) -> list[AgentNode]:
        rows = self._connection.execute("SELECT * FROM nodes ORDER BY created_at").fetchall()
        return [AgentNode(**dict(row)) for row in rows]

    def set_state(self, node_id: str, state: str, message: str | None = None) -> AgentNode:
        if state not in STATES:
            raise ValueError(f"Unknown state {state!r}; expected one of {STATES}")
        with self._lock:
            if self.get_node(node_id) is None:
                raise ValueError(f"Node does not exist: {node_id}")
            now = utc_now()
            self._connection.execute("UPDATE nodes SET state=?, updated_at=? WHERE id=?", (state, now, node_id))
            self._connection.commit()
            self._emit(Event(node_id, message or f"State changed to {state}", state))
        return self.get_node(node_id)  # type: ignore[return-value]

    def fork(self, parent_id: str, title: str, prompt: str) -> AgentNode:
        parent = self.get_node(parent_id)
        if parent is None:
            raise ValueError(f"Node does not exist: {parent_id}")
        return self.create_node(title, prompt, parent.id)

    def start(self, node_id: str, worker: Callable[[AgentNode], Iterable[str]]) -> threading.Thread:
        """Run a provider callback in the background and stream its messages as events."""
        node = self.set_state(node_id, "running", "Background execution started")

        def execute() -> None:
            try:
                for message in worker(node):
                    with self._lock:
                        self._emit(Event(node.id, message, "stream"))
                self.set_state(node.id, "completed", "Background execution completed")
            except Exception as error:
                self.set_state(node.id, "failed", f"Background execution failed: {error}")

        thread = threading.Thread(target=execute, name=f"constellation-{node.id}", daemon=True)
        thread.start()
        return thread

    def events_for(self, node_id: str) -> list[Event]:
        rows = self._connection.execute(
            "SELECT node_id,message,kind,created_at FROM events WHERE node_id=? ORDER BY id", (node_id,)
        ).fetchall()
        return [Event(**dict(row)) for row in rows]

    def tree_lines(self) -> list[tuple[AgentNode, str]]:
        nodes = self.list_nodes()
        children: dict[str | None, list[AgentNode]] = {}
        for node in nodes:
            children.setdefault(node.parent_id, []).append(node)
        result: list[tuple[AgentNode, str]] = []
        def visit(parent: str | None, prefix: str = "") -> None:
            siblings = children.get(parent, [])
            for index, node in enumerate(siblings):
                last = index == len(siblings) - 1
                result.append((node, prefix + ("`-- " if last else "|-- ")))
                visit(node.id, prefix + ("    " if last else "|   "))
        visit(None)
        return result

    def export_json(self) -> str:
        return json.dumps({"nodes": [asdict(n) for n in self.list_nodes()]}, indent=2)
