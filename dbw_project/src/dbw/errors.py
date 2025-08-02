"""Custom exceptions for dbw."""

from typing import Optional


class DbwError(Exception):
    """Base exception for all dbw errors."""
    
    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


class NetworkError(DbwError):
    """Network-related errors (clone, fetch)."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=3)


class GitError(DbwError):
    """Git operation errors."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=4)


class BranchMissing(GitError):
    """Requested branch doesn't exist."""
    pass


class DirtyWorktree(GitError):
    """Worktree has uncommitted changes."""
    pass


class DockerError(DbwError):
    """Docker-related errors."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=5)


class DockerUnavailable(DockerError):
    """Docker daemon not running or accessible."""
    pass


class ComposeError(DbwError):
    """Docker Compose errors."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=6)


class ComposeConflict(ComposeError):
    """Conflicting service definitions in compose."""
    pass


class ExtensionError(DbwError):
    """Extension-related errors."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=7)


class ExtensionInvalid(ExtensionError):
    """Extension YAML or Dockerfile invalid."""
    pass


class BakeFileError(DbwError):
    """Bake file generation or execution errors."""
    
    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=8)


class ConfigError(DbwError):
    """Configuration file errors."""
    pass