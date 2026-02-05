#!/usr/bin/env python3
"""
DuggerBootTools CLI Interface

Provides dbt-init command for bootstrapping projects with DLT DNA validation.
"""

import click
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .engine import BootEngine
from .scout import ProjectScout
from .harvest import HarvestEngine
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
@click.option(
    "--retrofit",
    is_flag=True,
    help="Retrofit existing directory instead of creating new project",
)
def init(name: str, template: str, path: str, force: bool, retrofit: bool) -> None:
    """Initialize a new project with DLT DNA validation or retrofit existing project."""
    try:
        engine = BootEngine()
        
        if retrofit:
            # Retrofit existing project
            project_path = Path(path) / name
            actions_performed = engine.retrofit_project(
                project_path=project_path,
                project_name=name,
                overwrite_ide=force,
            )
            
            performed_count = sum(1 for performed in actions_performed.values() if performed)
            
            console.print(
                Panel(
                    Text.from_markup(
                        f"🔧 Project '[bold green]{name}[/bold green]' retrofitted!\n\n"
                        f"📍 Location: {project_path}\n"
                        f"🧬 DNA: Upgraded to DLT standards\n"
                        f"🔧 Actions: {performed_count} components injected"
                    ),
                    title="Project Retrofitted",
                    border_style="green",
                )
            )
        else:
            # Create new project
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
        
        # Workflow hand-off
        console.print(
            Panel(
                Text.from_markup(
                    f"🚀 [bold blue]Next Step:[/bold blue] Verify ecosystem standing\n\n"
                    f"```bash\ncd {name}\ndgt status\n```\n\n"
                    f"This command will verify the project's health and show available DGT operations."
                ),
                title="Workflow Hand-off",
                border_style="blue",
            )
        )
        
    except DuggerBootError as e:
        console.print(
            Panel(
                Text.from_markup(f"❌ [bold red]{e.message}[/bold red]"),
                title="Operation Failed",
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
@click.option(
    "--path",
    default="C:\\Github",
    help="Ecosystem root directory to scan",
    show_default=True,
)
@click.option(
    "--suggest-recycle",
    is_flag=True,
    help="Suggest retrofit commands for old projects",
)
@click.option(
    "--output-map",
    help="Output path for ECOSYSTEM_MAP.md",
)
def scout(path: str, suggest_recycle: bool, output_map: str) -> None:
    """Scan ecosystem for harvestable components and retrofit candidates."""
    try:
        scout = ProjectScout(Path(path))
        inventory = scout.scan_ecosystem(suggest_recycle=suggest_recycle)
        
        # Display summary
        scout.display_summary(inventory)
        
        # Generate ecosystem map
        if output_map:
            scout.generate_ecosystem_map(inventory, Path(output_map))
            console.print(
                Panel(
                    Text.from_markup(f"📄 Ecosystem map generated: {output_map}"),
                    title="Documentation Created",
                    border_style="green",
                )
            )
        else:
            # Default to current directory
            default_path = Path.cwd() / "ECOSYSTEM_MAP.md"
            scout.generate_ecosystem_map(inventory, default_path)
            console.print(
                Panel(
                    Text.from_markup(f"📄 Ecosystem map generated: {default_path}"),
                    title="Documentation Created",
                    border_style="green",
                )
            )
        
    except DuggerBootError as e:
        console.print(
            Panel(
                Text.from_markup(f"❌ [bold red]{e.message}[/bold red]"),
                title="Scout Failed",
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
@click.argument("source_path", type=click.Path(exists=True))
@click.option(
    "--name",
    help="Component name (auto-generated if not provided)",
)
@click.option(
    "--type",
    help="Component type (python, chrome, shared, etc.)",
)
    "--description",
    help="Component description",
)
@click.option(
    "--component-type",
    help="Component type (python, chrome, shared, etc.)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing component",
)
def harvest(source_path: str, name: Optional[str], component_type: Optional[str], description: Optional[str], force: bool) -> None:
    """Harvest a component from an existing project."""
    try:
        harvest_engine = HarvestEngine()
        source = Path(source_path)
        
        # Auto-generate name if not provided
        if name is None:
            name = source.stem if source.is_file() else source.name
        
        success = harvest_engine.harvest_component(
            source_path=source,
            component_name=name,
            component_type=type or "shared",
            description=description,
            force=force,
        )
        
        if success:
            console.print(
                Panel(
                    Text.from_markup(f"✅ [bold green]Component '{name}' harvested successfully[/bold green]"),
                    title="Harvest Complete",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    Text.from_markup(f"❌ [bold red]Failed to harvest component '{name}'[/bold red]"),
                    title="Harvest Failed",
                    border_style="red",
                )
            )
            
    except DuggerBootError as e:
        console.print(
            Panel(
                Text.from_markup(f"❌ [bold red]{e.message}[/bold red]"),
                title="Harvest Failed",
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
@click.option(
    "--query",
    help="Search components by name, description, or tags",
)
def list_components(query: Optional[str]) -> None:
    """List all harvested components."""
    try:
        harvest_engine = HarvestEngine()
        
        if query:
            components = harvest_engine.search_components(query)
            console.print(f"\n[bold blue]Components matching '{query}':[/bold blue]\n")
        else:
            harvest_engine.display_components()
            return
        
        if not components:
            console.print("No matching components found.")
            return
        
        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("Category", style="magenta")
        table.add_column("Quality", justify="right")
        table.add_column("Files", justify="right")
        table.add_column("Tags", style="green")
        
        for component in components:
            table.add_row(
                component["name"],
                component["category"],
                f"{component['quality_score']:.2f}",
                str(len(component["files"])),
                ", ".join(component["tags"][:3])
            )
        
        console.print(table)
        
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
def list_templates() -> None:
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