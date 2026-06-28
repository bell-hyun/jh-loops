"""jh-loops CLI (typer + rich). Design §12.1."""

from __future__ import annotations

import typer
from rich.console import Console

from . import orchestrator
from .config import Config

app = typer.Typer(
    name="jh-loops",
    help="Issue-driven autonomous dev loop (poll -> dev -> verify -> PR).",
    no_args_is_help=True,
)
console = Console()


@app.command()
def init(repo: str = typer.Argument(..., help="owner/name")) -> None:
    """Install conventions (labels + issue template) into a target repo."""
    console.print(f"[bold]init[/] {repo} — TODO: run conventions/labels.sh + copy issue template")
    raise typer.Exit(code=1)


@app.command()
def tick(
    repo: str = typer.Argument(..., help="owner/name"),
    agent: str = typer.Option("claude", help="claude | codex | opencode"),
) -> None:
    """Run a single tick (process one issue)."""
    orchestrator.tick(Config(repo=repo, agent=agent))


@app.command()
def run(
    repo: str = typer.Argument(..., help="owner/name"),
    agent: str = typer.Option("claude", help="claude | codex | opencode"),
    interval: str = typer.Option("10m", help="poll interval"),
) -> None:
    """Run the loop on an interval (single-flight via cron + flock externally)."""
    orchestrator.run(Config(repo=repo, agent=agent, interval=interval))


if __name__ == "__main__":
    app()
