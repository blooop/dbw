"""Command-line interface for dbw."""

import sys
from dataclasses import dataclass

from rich.console import Console


from .compose import ComposeConfig, create_base_dockerfile, generate_compose_file
from .config import get_env
from .docker_runner import DockerRunner, parse_command_args

from .errors import DbwError
from .extension import (
    discover_repo_extensions,
    validate_extensions,
)
from .gitops import parse_repo_spec, setup_worktree
from .repo_config import get_working_directory, load_repo_config, merge_extensions


console = Console()


@dataclass
class LaunchConfig:
    """Configuration for launch command."""

    extensions: str = ""
    rebuild: bool = False
    no_gui: bool = False
    no_gpu: bool = False


# Main entrypoint: dbw <repo_spec> [command...]
def main():
    known_cmds = {
        "destroy",
        "list",
        "prune",
        "doctor",
        "update",
        "ext",
        "--help",
        "-h",
        "--version",
        "-v",
    }
    if len(sys.argv) > 1 and sys.argv[1] not in known_cmds:
        repo_spec = sys.argv[1]
        command = sys.argv[2:]
        try:
            owner, repo, branch, subfolder = parse_repo_spec(repo_spec)
            console.print(f"[bold blue]DBW[/bold blue] Starting {owner}/{repo}@{branch}")
            if subfolder:
                console.print(f"Working directory: {subfolder}")

            worktree_path, project_name = setup_worktree(owner, repo, branch)
            import git

            try:
                repo_obj = git.Repo(worktree_path)
                if repo_obj.bare:
                    raise Exception(
                        f"Worktree at {worktree_path} is bare, expected non-bare worktree."
                    )
                if repo_obj.active_branch.name != branch:
                    repo_obj.git.checkout(branch)
            except Exception as e:
                console.print(f"[red]Error ensuring worktree: {e}[/red]")
                raise

            repo_config = load_repo_config(worktree_path)
            repo_extensions = discover_repo_extensions(worktree_path)
            cli_extensions = []
            extensions = merge_extensions(cli_extensions, repo_extensions, repo_config.extensions)
            if extensions:
                validate_extensions(extensions)
            working_dir = get_working_directory(worktree_path, subfolder, repo_config)
            runner = DockerRunner(worktree_path, project_name)
            runner.check_docker_available()
            runner.check_compose_available()
            if runner.is_container_running():
                console.print("[green]Container already running, attaching...[green]")
                cmd_args = parse_command_args(command or [])
                exit_code = runner.exec_command(cmd_args)
                sys.exit(exit_code)
            base_image = get_env("DBW_BASE_IMAGE")
            create_base_dockerfile(worktree_path, base_image)
            compose_config = ComposeConfig(
                worktree_path=worktree_path,
                project_name=project_name,
                extensions=extensions,
                config=repo_config,
                base_image=base_image,
                working_dir=working_dir,
                enable_gpu=True,
                enable_x11=True,
            )
            generate_compose_file(compose_config)
            console.print("[yellow]Building and starting container...[yellow]")
            runner.build_images(force_rebuild=False)
            runner.start_container()
            cmd_args = parse_command_args(command or [])
            exit_code = runner.exec_command(cmd_args)
            sys.exit(exit_code)
        except DbwError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(e.exit_code)
    else:
        print("[red]Error: Unsupported command or missing repo spec.[/red]")
        sys.exit(2)
