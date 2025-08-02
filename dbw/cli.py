"""Command-line interface for dbw."""

import sys
from dataclasses import dataclass
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .compose import ComposeConfig, create_base_dockerfile, generate_compose_file
from .config import ensure_dirs, get_env
from .docker_runner import DockerRunner, parse_command_args
from .doctor import run_doctor
from .errors import DbwError
from .extension import (
    ExtensionCache,
    discover_repo_extensions,
    parse_extensions_list,
    validate_extensions,
)
from .gitops import parse_repo_spec, setup_worktree
from .log import setup_logging
from .repo_config import get_working_directory, load_repo_config, merge_extensions

app = typer.Typer(
    name="dbw",
    help="Docker Buildx/Bake Worktree - Fast dev containers with git worktree isolation",
    no_args_is_help=True,
)

console = Console()


@dataclass
class LaunchConfig:
    """Configuration for launch command."""

    extensions: str = ""
    rebuild: bool = False
    no_gui: bool = False
    no_gpu: bool = False


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"dbw {__version__}")
        raise typer.Exit()


@app.callback()
def dbw_main(
    version: Optional[bool] = typer.Option(  # pylint: disable=unused-argument
        None, "--version", "-v", callback=version_callback, is_eager=True
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose logging"),
) -> None:
    """DBW - Docker Buildx/Bake Worktree."""
    setup_logging(verbose)
    ensure_dirs()


@app.command()
def launch(
    spec: str = typer.Argument(..., help="Repository spec: owner/repo[@branch][#subfolder]"),
    command: Optional[list[str]] = typer.Argument(None, help="Command to run in container"),
    with_extensions: str = typer.Option("", "--with", help="Comma-separated list of extensions"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild of images"),
    no_gui: bool = typer.Option(False, "--no-gui", help="Disable X11 GUI forwarding"),
) -> None:
    """Launch or attach to a development environment."""
    try:
        # Parse repository specification
        owner, repo, branch, subfolder = parse_repo_spec(spec)

        console.print(f"[bold blue]DBW[/bold blue] Launching {owner}/{repo}@{branch}")
        if subfolder:
            console.print(f"Working directory: {subfolder}")

        # Setup git worktree
        worktree_path, project_name = setup_worktree(owner, repo, branch)

        # Load repository configuration
        repo_config = load_repo_config(worktree_path)

        # Discover repository extensions
        repo_extensions = discover_repo_extensions(worktree_path)

        # Parse CLI extensions
        cli_extensions = parse_extensions_list(with_extensions)

        # Merge extensions from all sources
        extensions = merge_extensions(cli_extensions, repo_extensions, repo_config.extensions)

        # Validate extensions exist
        if extensions:
            validate_extensions(extensions)

        # Determine working directory
        working_dir = get_working_directory(worktree_path, subfolder, repo_config)

        # Create Docker runner
        runner = DockerRunner(worktree_path, project_name)

        # Check Docker availability
        runner.check_docker_available()
        runner.check_compose_available()

        # Check if container is already running
        if runner.is_container_running() and not rebuild:
            console.print("[green]Container already running, attaching...[/green]")

            # Execute command or start shell
            cmd_args = parse_command_args(command or [])
            exit_code = runner.exec_command(cmd_args)
            sys.exit(exit_code)

        # Create base image and Dockerfile
        base_image = get_env("DBW_BASE_IMAGE")
        create_base_dockerfile(worktree_path, base_image)

        # Generate docker-compose.yml
        compose_config = ComposeConfig(
            worktree_path=worktree_path,
            project_name=project_name,
            extensions=extensions,
            config=repo_config,
            base_image=base_image,
            working_dir=working_dir,
            enable_gpu=True,  # Default to GPU enabled
            enable_x11=not no_gui,
        )
        generate_compose_file(compose_config)

        # Build/start container
        console.print("[yellow]Building and starting container...[/yellow]")
        runner.build_images(force_rebuild=rebuild)
        runner.start_container()

        # Execute command or start shell
        cmd_args = parse_command_args(command or [])
        exit_code = runner.exec_command(cmd_args)
        sys.exit(exit_code)

    except DbwError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(e.exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)


@app.command()
def destroy(
    spec: str = typer.Argument(..., help="Repository spec: owner/repo[@branch]"),
    remove_volumes: bool = typer.Option(False, "--volumes", help="Remove volumes too"),
) -> None:
    """Stop and remove a development environment."""
    try:
        owner, repo, branch, _ = parse_repo_spec(spec)
        worktree_path, project_name = setup_worktree(owner, repo, branch)

        runner = DockerRunner(worktree_path, project_name)

        console.print(f"[yellow]Destroying {project_name}...[/yellow]")
        runner.remove_container(remove_volumes=remove_volumes)
        console.print("[green]Environment destroyed[/green]")

    except DbwError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(e.exit_code)


@app.command("list")
def list_envs() -> None:
    """List active development environments."""
    try:
        import subprocess

        # Get running containers with dbw prefix
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=dbw_",
                "--format",
                "table {{.Names}}\t{{.Status}}\t{{.Ports}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            console.print("[bold]Active DBW Environments:[/bold]")
            console.print(result.stdout)
        else:
            console.print("[yellow]No active environments found[/yellow]")

    except Exception as e:
        console.print(f"[red]Error listing environments:[/red] {e}")
        sys.exit(1)


@app.command()
def prune(
    days: int = typer.Option(7, "--days", help="Remove images older than N days"),
    force: bool = typer.Option(False, "--force", help="Don't ask for confirmation"),
) -> None:
    """Clean up old images and volumes."""
    try:
        import subprocess

        if not force:
            confirm = typer.confirm(f"Remove DBW images and volumes older than {days} days?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return

        console.print("[yellow]Pruning old images and volumes...[/yellow]")

        # Prune images
        subprocess.run(
            [
                "docker",
                "image",
                "prune",
                "-f",
                "--filter",
                f"until={days * 24}h",
                "--filter",
                "label=dbw=true",
            ],
            check=False,
        )

        # Prune volumes
        subprocess.run(
            [
                "docker",
                "volume",
                "prune",
                "-f",
                "--filter",
                f"until={days * 24}h",
            ],
            check=False,
        )

        console.print("[green]Cleanup complete[/green]")

    except Exception as e:
        console.print(f"[red]Error during cleanup:[/red] {e}")
        sys.exit(1)


# Extension management commands
ext_app = typer.Typer(name="ext", help="Manage extensions")
app.add_typer(ext_app)


@ext_app.command("list")
def ext_list() -> None:
    """List available extensions."""
    cache = ExtensionCache()
    extensions = cache.list_extensions()

    if extensions:
        table = Table(title="Available Extensions")
        table.add_column("Name", style="bold")
        table.add_column("Path")

        for ext_name in sorted(extensions):
            ext_path = cache.get_extension_path(ext_name)
            table.add_row(ext_name, str(ext_path))

        console.print(table)
    else:
        console.print("[yellow]No extensions found[/yellow]")


@ext_app.command("add")
def ext_add(
    name: str = typer.Argument(..., help="Extension name"),
    source: str = typer.Argument(..., help="Source URL or local path"),
) -> None:
    """Add an extension."""
    try:
        cache = ExtensionCache()
        cache.add_extension(name, source)
        console.print(f"[green]Extension '{name}' added successfully[/green]")

    except DbwError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(e.exit_code)


@ext_app.command("remove")
def ext_remove(
    name: str = typer.Argument(..., help="Extension name"),
) -> None:
    """Remove an extension."""
    try:
        cache = ExtensionCache()
        cache.remove_extension(name)
        console.print(f"[green]Extension '{name}' removed[/green]")

    except DbwError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(e.exit_code)


@app.command()
def doctor() -> None:
    """Run system diagnostics."""
    exit_code = run_doctor()
    sys.exit(exit_code)


@app.command()
def update() -> None:
    """Update dbw and base images."""
    try:
        import subprocess

        console.print("[yellow]Updating base images...[/yellow]")

        base_image = get_env("DBW_BASE_IMAGE")
        subprocess.run(["docker", "pull", base_image], check=True)

        console.print("[green]Update complete[/green]")

    except Exception as e:
        console.print(f"[red]Error updating:[/red] {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
