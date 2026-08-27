"""Dual-pane Textual application."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Label, ListItem, ListView, Static

from constellation.core.orchestrator import AgentNode, Orchestrator


class ConstellationApp(App[None]):
    CSS = """
    Screen { background: #081018; color: #d8e8ed; }
    Header { background: #102a35; color: #7fe9df; }
    #body { height: 1fr; }
    #tree-pane { width: 42%; border: solid #24525a; padding: 1; }
    #detail-pane { width: 58%; border: solid #24525a; padding: 1 2; }
    #tree { height: 1fr; }
    ListItem { padding: 0 1; }
    ListItem.--highlight { background: #17484c; color: #ffffff; }
    #detail { height: 1fr; overflow-y: auto; }
    .running { color: #63e6be; }
    .completed { color: #6e858b; }
    .needs-input { color: #ffd166; }
    .parked { color: #8aa0aa; }
    Footer { background: #102a35; }
    """
    BINDINGS = [("r", "refresh", "Refresh"), ("q", "quit", "Quit")]

    def __init__(self, orchestrator: Orchestrator, **kwargs) -> None:
        super().__init__(**kwargs)
        self.orchestrator = orchestrator
        self.orchestrator.subscribe(lambda _: self.call_from_thread(self.refresh_view))

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="tree-pane"):
                yield Static(id="stats", classes="title")
                yield ListView(id="tree")
            with Vertical(id="detail-pane"):
                yield Static("EVENT STREAM", classes="title")
                yield Static("Select a branch to inspect its causal chain.", id="detail")
        yield Static("forest  run  attach/branch  next/flow  search  mcp status", id="commands")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_view()

    def action_refresh(self) -> None:
        self.refresh_view()

    def refresh_view(self) -> None:
        nodes = self.orchestrator.list_nodes()
        active = sum(node.state == "running" for node in nodes)
        self.query_one("#stats", Static).update(
            f"✦ CONSTELLATION / FOREST    active {active}  nodes {len(nodes)}  mcp 0"
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
        lines = [f"[{node.state.upper()}] {node.title}", f"prompt: {node.prompt}", "", "EVENTS"]
        lines.extend(f"{event.created_at}  {event.message}" for event in self.orchestrator.events_for(node.id))
        self.query_one("#detail", Static).update("\n".join(lines))

    @staticmethod
    def _glyph(node: AgentNode) -> str:
        return {"running": "◉", "completed": "✓", "needs-input": "!", "parked": "○", "failed": "×"}.get(node.state, "·")
