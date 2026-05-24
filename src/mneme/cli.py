"""Mneme command-line interface."""

from __future__ import annotations

import asyncio
import sys

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from mneme.agent import Agent, AgentConfig
from mneme.config import load_settings
from mneme.memory.embeddings import Embedder
from mneme.memory.store import MemoryStore
from mneme.memory.types import MemoryKind

app = typer.Typer(
    help="Mneme — local-first AI agent with long-term memory.",
    no_args_is_help=True,
    add_completion=False,
)
memory_app = typer.Typer(help="Inspect and manage stored memories.")
app.add_typer(memory_app, name="memory")

console = Console()


def _make_agent(provider: str | None, model: str | None) -> Agent:
    settings = load_settings()
    embedder = Embedder(settings.embedding_model)
    store = MemoryStore(path=settings.data_dir, embedder=embedder)
    config = AgentConfig(
        provider=provider or settings.provider,
        model=model or settings.model,
    )
    return Agent(config, store=store)


def _make_store() -> MemoryStore:
    settings = load_settings()
    return MemoryStore(path=settings.data_dir, embedder=Embedder(settings.embedding_model))


# ── chat ────────────────────────────────────────────────────────────────

@app.command()
def chat(
    provider: str | None = typer.Option(None, "--provider", "-p"),
    model: str | None = typer.Option(None, "--model", "-m"),
    stream: bool = typer.Option(True, "--stream/--no-stream"),
) -> None:
    """Interactive chat with long-term memory."""
    agent = _make_agent(provider, model)
    console.print(
        f"[dim]Mneme · provider={agent.config.provider} · model={agent.config.model}[/dim]"
    )
    console.print("[dim]Type 'exit' or Ctrl-D to quit.[/dim]\n")

    async def run() -> None:
        try:
            while True:
                try:
                    user = console.input("[bold cyan]you ›[/bold cyan] ")  # noqa: RUF001
                except EOFError:
                    break
                if not user.strip():
                    continue
                if user.strip().lower() in {"exit", "quit", ":q"}:
                    break
                console.print("[bold magenta]mneme ›[/bold magenta] ", end="")  # noqa: RUF001
                if stream:
                    async for piece in agent.stream(user):
                        console.print(piece, end="", soft_wrap=True)
                    console.print()
                else:
                    answer = await agent.chat(user)
                    console.print(Markdown(answer))
        finally:
            agent.close()

    asyncio.run(run())


@app.command()
def ask(
    prompt: str = typer.Argument(..., help="The question to ask."),
    provider: str | None = typer.Option(None, "--provider", "-p"),
    model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
    """One-shot question, prints the answer to stdout."""
    agent = _make_agent(provider, model)
    try:
        answer = asyncio.run(agent.chat(prompt))
    finally:
        agent.close()
    console.print(answer)


# ── memory subcommands ─────────────────────────────────────────────────

@memory_app.command("list")
def memory_list(
    kind: str | None = typer.Option(None, "--kind", "-k"),
    limit: int = typer.Option(20, "--limit", "-n"),
) -> None:
    """List stored memories."""
    store = _make_store()
    try:
        mk = MemoryKind(kind) if kind else None
        rows = store.list(kind=mk, limit=limit)
        _print_memory_table(rows)
    finally:
        store.close()


@memory_app.command("search")
def memory_search(
    query: str = typer.Argument(...),
    kind: str | None = typer.Option(None, "--kind", "-k"),
    k: int = typer.Option(10, "--top", "-n"),
) -> None:
    """Vector + heuristic search across memories."""
    store = _make_store()
    try:
        mk = MemoryKind(kind) if kind else None
        results = store.search(query, kind=mk, k=k)
        if not results:
            console.print("[yellow]No matches.[/yellow]")
            return
        table = Table(show_lines=False, header_style="bold")
        table.add_column("score", justify="right")
        table.add_column("kind")
        table.add_column("content", overflow="fold")
        table.add_column("id", style="dim")
        for mem, score in results:
            table.add_row(f"{score:.3f}", mem.kind.value, mem.content, mem.id[:8])
        console.print(table)
    finally:
        store.close()


@memory_app.command("forget")
def memory_forget(memory_id: str = typer.Argument(...)) -> None:
    """Delete a memory by id (prefix match allowed)."""
    store = _make_store()
    try:
        if len(memory_id) < 32:
            matches = [m for m in store.list(limit=10_000) if m.id.startswith(memory_id)]
            if not matches:
                console.print("[red]No memory matches that id prefix.[/red]")
                raise typer.Exit(code=1)
            if len(matches) > 1:
                console.print("[red]Ambiguous prefix, refine.[/red]")
                raise typer.Exit(code=1)
            memory_id = matches[0].id
        store.delete(memory_id)
        console.print(f"[green]Removed {memory_id}[/green]")
    finally:
        store.close()


@memory_app.command("stats")
def memory_stats() -> None:
    """Show counts per memory kind."""
    store = _make_store()
    try:
        table = Table(header_style="bold")
        table.add_column("kind")
        table.add_column("count", justify="right")
        total = 0
        for kind in MemoryKind:
            c = store.count(kind)
            total += c
            table.add_row(kind.value, str(c))
        table.add_row("total", str(total), style="bold")
        console.print(table)
    finally:
        store.close()


@memory_app.command("decay")
def memory_decay(
    half_life: float = typer.Option(30.0, "--half-life"),
    importance_floor: float = typer.Option(0.2, "--importance"),
) -> None:
    """Prune low-value episodic memories past their half-life."""
    store = _make_store()
    try:
        n = store.decay(half_life_days=half_life, importance_floor=importance_floor)
        console.print(f"[green]Pruned {n} memories.[/green]")
    finally:
        store.close()


# ── serve ──────────────────────────────────────────────────────────────

@app.command()
def serve(
    host: str | None = typer.Option(None, "--host"),
    port: int | None = typer.Option(None, "--port"),
    provider: str | None = typer.Option(None, "--provider", "-p"),
    model: str | None = typer.Option(None, "--model", "-m"),
) -> None:
    """Start the REST API server (OpenAI-compatible)."""
    import uvicorn

    from mneme.api.server import create_app

    settings = load_settings()
    fastapi_app = create_app(
        provider=provider or settings.provider,
        model=model or settings.model,
    )
    uvicorn.run(
        fastapi_app,
        host=host or settings.host,
        port=port or settings.port,
        log_level="info",
    )


@app.command()
def remember(
    content: str = typer.Argument(...),
    importance: float = typer.Option(0.6, "--importance", "-i"),
) -> None:
    """Add an episodic memory manually."""
    settings = load_settings()
    store = MemoryStore(path=settings.data_dir, embedder=Embedder(settings.embedding_model))
    try:
        from mneme.memory.types import EpisodicMemory

        mem = store.add(
            EpisodicMemory(content=content, importance=importance, source="manual")
        )
        console.print(f"[green]Saved {mem.id[:8]}[/green]")
    finally:
        store.close()


@app.command()
def version() -> None:
    """Print the version."""
    from mneme import __version__

    console.print(__version__)


def _print_memory_table(rows: list) -> None:
    if not rows:
        console.print("[yellow]No memories yet.[/yellow]")
        return
    table = Table(header_style="bold")
    table.add_column("id", style="dim")
    table.add_column("kind")
    table.add_column("when")
    table.add_column("imp", justify="right")
    table.add_column("content", overflow="fold")
    for m in rows:
        table.add_row(
            m.id[:8],
            m.kind.value,
            m.created_at.strftime("%Y-%m-%d %H:%M"),
            f"{m.importance:.2f}",
            m.content,
        )
    console.print(table)


def main() -> None:  # pragma: no cover - script entrypoint
    try:
        app()
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":  # pragma: no cover
    main()
