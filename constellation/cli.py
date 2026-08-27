"""Command-line entry point."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from constellation.core.orchestrator import Orchestrator
from constellation.tui.app import ConstellationApp

app = typer.Typer(help="Explore and orchestrate concurrent agent branches.")


def open_orchestrator() -> Orchestrator:
    return Orchestrator(os.environ.get("CONSTELLATION_DB", ".constellation/state.db"))


@app.command()
def run(prompt: str, interactive: bool = typer.Option(False, "--interactive", "-i")) -> None:
    """Create a root agent branch and optionally open the forest."""
    orchestrator = open_orchestrator()
    node = orchestrator.create_node(prompt[:48], prompt)
    orchestrator.set_state(node.id, "running", "Agent branch started")
    typer.echo(f"Created branch {node.id}: {node.title}")
    if interactive:
        ConstellationApp(orchestrator).run()


@app.command()
def forest() -> None:
    """Launch the interactive dependency forest."""
    orchestrator = open_orchestrator()
    ConstellationApp(orchestrator).run()


@app.command()
def branch(resume: str = typer.Option(..., "--resume", help="Branch id to resume.")) -> None:
    """Resume a parked or waiting branch."""
    orchestrator = open_orchestrator()
    node = orchestrator.set_state(resume, "running", "Branch resumed")
    typer.echo(f"Resumed {node.id}: {node.title}")


@app.command("mcp")
def mcp_status(action: str = typer.Argument("status")) -> None:
    """Show bound MCP servers for this process."""
    if action != "status":
        raise typer.BadParameter("Only 'status' is currently supported")
    typer.echo("No MCP servers bound. Bind servers through MCPClientManager in your runner.")


if __name__ == "__main__":
    app()
