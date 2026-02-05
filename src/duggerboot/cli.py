#!/usr/bin/env python3
"""
DuggerBootTools CLI Interface

Provides dbt-init command for bootstrapping projects with DLT DNA validation.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .engine import BootEngine
from .exceptions import DuggerBootError

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """DuggerBootTools - Project bootstrapping for the DuggerLinkTools ecosystem."""
    pass


@main.command()
@click.argument("name")
@click.option(
    "--template",
    default="standard",
    help="Template type to use (default: standard)",
    show_default=True,
)
@click.option(
    "--path",
    default=".",
    help="Parent directory for new project",
    show_default=True,
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing directory",
)
def init(name: str, template: str, path: str, force: bool) -> None:
    """Initialize a new project with DLT DNA validation."""
    try:
        engine = BootEngine()
        project_path = engine.bootstrap_project(
            name=name,
            template_type=template,
            parent_path=Path(path),
            force=force,
        )
        
        console.print(
            Panel(
                Text.from_markup(
                    f"✅ Project '[bold green]{name}[/bold green]' successfully initialized!\n\n"
                    f"📍 Location: {project_path}\n"
                    f"🧬 DNA: Validated against DLT schemas\n"
                    f"🔥 Git: Initialized with initial commit"
                ),
                title="Project Bootstrapped",
                border_style="green",
            )
        )
        
    except DuggerBootError as e:
        console.print(
            Panel(
                Text.from_markup(f"❌ [bold red]{e.message}[/bold red]"),
                title="Bootstrapping Failed",
                border_style="red",
            )
        )
        raise click.ClickException(str(e))
    except Exception as e:
        console.print(
            Panel(
                Text.from_markup(f"💥 Unexpected error: {e}"),
                title="System Error",
                border_style="red",
            )
        )
        raise click.ClickException(str(e))


@main.command()
def list() -> None:
    """List available project templates."""
    try:
        engine = BootEngine()
        templates = engine.list_templates()
        
        if not templates:
            console.print("No templates found.")
            return
            
        console.print(Panel("Available Templates", border_style="blue"))
        for template in templates:
            console.print(f"  • {template}")
            
    except DuggerBootError as e:
        console.print(f"❌ Error listing templates: {e.message}")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()