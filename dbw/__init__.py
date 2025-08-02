"""DBW - Docker Buildx/Bake Worktree

Fast dev containers with git worktree isolation and extension caching.
"""

__version__ = "0.2.0"

# Import main components for easy access
from .cli import main
from .errors import DbwError
from .gitops import parse_repo_spec, setup_worktree
from .extension import ExtensionCache
from .docker_runner import DockerRunner

__all__ = [
    "main",
    "DbwError",
    "parse_repo_spec",
    "setup_worktree",
    "ExtensionCache",
    "DockerRunner",
]
