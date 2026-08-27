"""Command-line entry point."""

from __future__ import annotations

import os

import typer

from constellation.core.orchestrator import Orchestrator
from constellation.tui.app import ConstellationApp

app = typer.Typer(help="Explore and orchestrate concurrent agent branches.")


def open_orchestrator() -> Orchestrator:
    return Orchestrator(os.environ.get("CONSTELLATION_DB", ".constellation/state.db"))


@app.command()
def run(prompt: str, interactive: bool = typer.Option(False, "--interactive", "-i")) -> None:
    """Launch a mission and optionally open the star map."""
    orchestrator = open_orchestrator()
    node = orchestrator.create_node(prompt[:48], prompt)
    orchestrator.set_state(node.id, "running", "Agent branch started")
    typer.echo(f"Created branch {node.id}: {node.title}")
    if interactive:
        ConstellationApp(orchestrator).run()


@app.command("stars")
def stars() -> None:
    """Launch the interactive Constellation star map."""
    orchestrator = open_orchestrator()
    ConstellationApp(orchestrator).run()


@app.command("forest", hidden=True)
def forest_alias() -> None:
    """Legacy alias for stars."""
    stars()


@app.command("orbit")
def orbit(resume: str = typer.Option(..., "--resume", help="Mission node id to resume.")) -> None:
    """Resume a parked or waiting mission node."""
    orchestrator = open_orchestrator()
    node = orchestrator.set_state(resume, "running", "Branch resumed")
    typer.echo(f"Resumed {node.id}: {node.title}")


@app.command("branch", hidden=True)
def branch_alias(resume: str = typer.Option(..., "--resume", help="Mission node id to resume.")) -> None:
    """Legacy alias for orbit."""
    orbit(resume)


@app.command("mcp")
def mcp_status(action: str = typer.Argument("status")) -> None:
    """Show bound MCP servers for this process."""
    if action != "status":
        raise typer.BadParameter("Only 'status' is currently supported")
    typer.echo("No MCP servers bound. Bind servers through MCPClientManager in your runner.")


if __name__ == "__main__":
    app()
