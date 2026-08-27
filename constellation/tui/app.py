"""Dual-pane Textual application."""

from __future__ import annotations

import threading

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from constellation.core.orchestrator import AgentNode, Orchestrator


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [("y", "confirm_yes", "Yes"), ("n", "confirm_no", "No")]

    CSS = """
    ConfirmScreen { align: center middle; background: rgba(8, 6, 20, 0.72); }
    #confirm-box { width: 58; height: auto; background: #211d3d; border: thick #877BCA; padding: 2 3; }
    #confirm-message { margin-bottom: 1; color: #ebe8f5; }
    #confirm-actions { height: 3; align: center middle; }
    #confirm-actions Button { margin: 0 1; }
    #confirm-yes { background: #877BCA; color: #0e0d1c; }
    #confirm-no { background: #3c3764; color: #ebe8f5; }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-box"):
            yield Label(self.message, id="confirm-message")
            with Horizontal(id="confirm-actions"):
                yield Button("Yes", id="confirm-yes", variant="primary")
                yield Button("No", id="confirm-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")

    def action_confirm_yes(self) -> None:
        self.dismiss(True)

    def action_confirm_no(self) -> None:
        self.dismiss(False)


class ConstellationApp(App[None]):
    CSS = """
    Screen { background: #0e0d1c; color: #ebe8f5; }
    Header { background: #1b1830; color: #877BCA; }
    #body { height: 1fr; }
    #tree-pane { width: 42%; background: #17152a; border: solid #3c3764; padding: 1; }
    #detail-pane { width: 58%; background: #121124; border: solid #3c3764; padding: 1 2; }
    #tree { height: 1fr; scrollbar-color: #5b5490; }
    ListItem { padding: 0 1; color: #bcb7d2; }
    ListItem.--highlight { background: #302b55; color: #ffffff; }
    .title { color: #a69be6; text-style: bold; }
    #detail { height: 1fr; overflow-y: auto; }
    .running { color: #b7a9ff; }
    .completed { color: #77718f; }
    .needs-input { color: #f6c85f; }
    .parked { color: #9892b0; }
    .failed { color: #ff8b7b; }
    Footer { background: #1b1830; color: #bcb7d2; }
    """
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("s", "stop_selected", "Stop"),
        ("d", "delete_selected", "Delete"),
        Binding("ctrl+p", "command_palette", "palette"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, orchestrator: Orchestrator, **kwargs) -> None:
        super().__init__(**kwargs)
        self.title = "Constellation"
        self.orchestrator = orchestrator
        self._ui_thread: threading.Thread | None = None
        self.orchestrator.subscribe(self._on_orchestrator_event)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="tree-pane"):
                yield Static(id="stats", classes="title")
                yield ListView(id="tree")
            with Vertical(id="detail-pane"):
                yield Static("SIGNAL STREAM", classes="title")
                yield Static("Select a mission node to inspect its causal chain.", id="detail")
        yield Footer()

    def on_mount(self) -> None:
        self._ui_thread = threading.current_thread()
        self.refresh_view()
        self.query_one("#tree", ListView).focus()

    def _on_orchestrator_event(self, _event) -> None:
        if threading.current_thread() is self._ui_thread:
            self.refresh_view()
        else:
            self.call_from_thread(self.refresh_view)

    def action_refresh(self) -> None:
        self.refresh_view()

    def refresh_view(self) -> None:
        nodes = self.orchestrator.list_nodes()
        active = sum(node.state == "running" for node in nodes)
        self.query_one("#stats", Static).update(
            f"✦ CONSTELLATION / STAR MAP    active {active}  nodes {len(nodes)}  mcp 0"
        )
        tree = self.query_one("#tree", ListView)
        selected = tree.index
        tree.clear()
        for node, prefix in self.orchestrator.tree_lines():
            tree.mount(ListItem(Label(f"{prefix}{self._glyph(node)} {node.title}"), name=node.id, classes=node.state))
        if tree.children:
            tree.index = min(selected if selected is not None else 0, len(tree.children) - 1)
            self._show_selected()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._show_node(event.item.name)

    def _show_selected(self) -> None:
        tree = self.query_one("#tree", ListView)
        if tree.highlighted_child:
            self._show_node(tree.highlighted_child.name)

    def _show_node(self, node_id: str | None) -> None:
        if not node_id:
            return
        node = self.orchestrator.get_node(node_id)
        if node is None:
            return
        lines = [
            f"[{node.state.upper()}] {node.title}",
            f"id: {node.id}",
            f"mission: {node.prompt}",
            "",
            "KEYS: s stop  d delete  ctrl+p palette",
            "",
            "SIGNALS",
        ]
        lines.extend(f"{event.created_at}  {event.message}" for event in self.orchestrator.events_for(node.id))
        self.query_one("#detail", Static).update("\n".join(lines))

    def _selected_node_id(self) -> str | None:
        tree = self.query_one("#tree", ListView)
        item = tree.highlighted_child
        if item is None and tree.index is not None and tree.children:
            item = tree.children[tree.index]
        return item.name if item else None

    def action_stop_selected(self) -> None:
        node_id = self._selected_node_id()
        if node_id:
            self.push_screen(
                ConfirmScreen(f"Stop mission {node_id}?"),
                lambda confirmed: self._stop_confirmed(node_id, confirmed),
            )

    def action_delete_selected(self) -> None:
        node_id = self._selected_node_id()
        if node_id:
            self.push_screen(
                ConfirmScreen(f"Delete mission subtree {node_id}?"),
                lambda confirmed: self._delete_confirmed(node_id, confirmed),
            )

    def _stop_confirmed(self, node_id: str, confirmed: bool) -> None:
        if confirmed:
            self.orchestrator.stop(node_id)
            self.notify(f"Stopped mission {node_id}")

    def _delete_confirmed(self, node_id: str, confirmed: bool) -> None:
        if confirmed:
            self.orchestrator.delete(node_id)
            self.notify(f"Deleted mission subtree {node_id}")
            self.refresh_view()

    @staticmethod
    def _glyph(node: AgentNode) -> str:
        return {"running": "◉", "completed": "✓", "needs-input": "!", "parked": "○", "failed": "×"}.get(node.state, "·")
