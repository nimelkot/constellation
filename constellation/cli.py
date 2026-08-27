"""Command-line entry point."""

from __future__ import annotations

import os

import typer

from constellation.core.orchestrator import Orchestrator
from constellation.core.auth import APIKeyStore
from constellation.core.demo import demo_worker
from constellation.tui.app import ConstellationApp

app = typer.Typer(help="Explore and orchestrate concurrent agent branches.")


def open_orchestrator() -> Orchestrator:
    return Orchestrator(os.environ.get("CONSTELLATION_DB", ".constellation/state.db"))


@app.command()
def run(prompt: str, interactive: bool = typer.Option(False, "--interactive", "-i")) -> None:
    """Launch a mission and optionally open the star map."""
    orchestrator = open_orchestrator()
    node = orchestrator.create_node(prompt[:48], prompt)
    typer.echo(f"Created branch {node.id}: {node.title}")
    if interactive:
        interface = ConstellationApp(orchestrator)
        orchestrator.start(node.id, demo_worker)
        interface.run()
    else:
        worker = orchestrator.start(node.id, demo_worker)
        worker.join()
        typer.echo(f"Mission {node.id} completed")


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
def orbit(
    resume: str | None = typer.Option(None, "--resume", help="Mission node id to resume."),
    parent: str | None = typer.Option(None, "--from", help="Parent node id for a sub-mission."),
    title: str | None = typer.Option(None, "--title", help="Sub-mission title."),
    prompt: str | None = typer.Option(None, "--prompt", help="Sub-mission prompt."),
) -> None:
    """Resume a node or create a sub-mission in its orbit."""
    orchestrator = open_orchestrator()
    if parent:
        if not title or not prompt:
            raise typer.BadParameter("--from requires both --title and --prompt")
        node = orchestrator.fork(parent, title, prompt)
        typer.echo(f"Created sub-mission {node.id}: {node.title}")
        return
    if not resume:
        raise typer.BadParameter("Provide --resume or --from")
    node = orchestrator.set_state(resume, "running", "Mission resumed")
    typer.echo(f"Resumed {node.id}: {node.title}")


@app.command("branch", hidden=True)
def branch_alias(resume: str = typer.Option(..., "--resume", help="Mission node id to resume.")) -> None:
    """Legacy alias for orbit."""
    orbit(resume=resume)


@app.command()
def status() -> None:
    """Show saved mission nodes and their current states."""
    orchestrator = open_orchestrator()
    nodes = orchestrator.list_nodes()
    if not nodes:
        typer.echo("No missions recorded.")
        return
    for node in nodes:
        typer.echo(f"{node.id}  {node.state:<12}  {node.title}")


@app.command()
def stop(node_id: str = typer.Argument(..., help="Mission node id to stop.")) -> None:
    """Stop a mission and park it in the star map."""
    orchestrator = open_orchestrator()
    node = orchestrator.stop(node_id)
    typer.echo(f"Stopped {node.id}: {node.title}")


@app.command()
def delete(
    node_id: str = typer.Argument(..., help="Mission node id to delete."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Delete a mission and all of its sub-missions."""
    if not yes and not typer.confirm(f"Delete mission subtree {node_id}?"):
        typer.echo("Delete cancelled.")
        return
    open_orchestrator().delete(node_id)
    typer.echo(f"Deleted mission subtree {node_id}")


@app.command("api-key")
def api_key(
    action: str = typer.Argument("create"),
    label: str = typer.Option("default", "--label", help="Label for the new local key."),
) -> None:
    """Create a local API key for future provider integrations."""
    if action != "create":
        raise typer.BadParameter("Only 'create' is currently supported")
    token = APIKeyStore().create(label)
    typer.echo("API key created. Store this value securely; it will not be shown again:")
    typer.echo(token)


@app.command("mcp")
def mcp_status(action: str = typer.Argument("status")) -> None:
    """Show bound MCP servers for this process."""
    if action != "status":
        raise typer.BadParameter("Only 'status' is currently supported")
    typer.echo("No MCP servers bound. Bind servers through MCPClientManager in your runner.")


if __name__ == "__main__":
    app()
