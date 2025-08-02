"""Shared pytest fixtures and configuration for dbw tests."""
# pylint: disable=redefined-outer-name

import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import git

from dbw.extension import ExtensionCache


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_workspaces_dir(temp_dir: Path) -> Generator[Path, None, None]:  # pylint: disable=redefined-outer-name
    """Mock the workspaces directory."""
    workspaces_dir = temp_dir / "workspaces"
    workspaces_dir.mkdir(parents=True, exist_ok=True)

    with patch("dbw.gitops.get_workspaces_dir", return_value=workspaces_dir):
        yield workspaces_dir


@pytest.fixture
def mock_extensions_dir(temp_dir: Path) -> Generator[Path, None, None]:  # pylint: disable=redefined-outer-name
    """Mock the extensions directory."""
    extensions_dir = temp_dir / "extensions"
    extensions_dir.mkdir(parents=True, exist_ok=True)

    with patch("dbw.extension.get_extensions_dir", return_value=extensions_dir):
        yield extensions_dir


@pytest.fixture
def mock_cache_dir(temp_dir: Path) -> Generator[Path, None, None]:  # pylint: disable=redefined-outer-name
    """Mock the buildx cache directory."""
    cache_dir = temp_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    with patch("dbw.extension.get_buildx_cache_dir", return_value=cache_dir):
        yield cache_dir


@pytest.fixture
def mock_bare_repo(temp_dir: Path) -> Generator[git.Repo, None, None]:  # pylint: disable=redefined-outer-name
    """Create a mock bare git repository."""
    bare_repo_path = temp_dir / "test_repo.git"

    # Create a regular repo first
    regular_repo_path = temp_dir / "regular_repo"
    regular_repo = git.Repo.init(regular_repo_path)

    # Add initial commit
    test_file = regular_repo_path / "README.md"
    test_file.write_text("# Test Repository\n")
    regular_repo.index.add([str(test_file)])
    regular_repo.index.commit("Initial commit")

    # Clone as bare repo
    bare_repo = git.Repo.clone_from(regular_repo_path, bare_repo_path, bare=True)

    yield bare_repo


@pytest.fixture
def mock_worktree(temp_dir: Path, mock_bare_repo: git.Repo) -> Generator[Path, None, None]:  # pylint: disable=redefined-outer-name
    """Create a mock worktree."""
    worktree_path = temp_dir / "test_repo-main"

    # Add worktree
    mock_bare_repo.git.worktree("add", str(worktree_path), "main")

    yield worktree_path


@pytest.fixture
def extension_cache(mock_extensions_dir: Path) -> ExtensionCache:  # pylint: disable=unused-argument
    """Create an ExtensionCache instance with mocked directory."""
    # The mock_extensions_dir fixture patches get_extensions_dir()
    # so ExtensionCache() will use the mocked directory
    return ExtensionCache()


@pytest.fixture
def sample_extension(mock_extensions_dir: Path) -> Path:  # pylint: disable=redefined-outer-name
    """Create a sample extension for testing."""
    ext_dir = mock_extensions_dir / "test_ext"
    ext_dir.mkdir(parents=True, exist_ok=True)

    # Create docker-compose fragment
    fragment_content = """
version: '3.8'
services:
  dev:
    environment:
      TEST_VAR: "test_value"
"""
    (ext_dir / "docker-compose.fragment.yml").write_text(fragment_content)

    # Create Dockerfile
    dockerfile_content = """
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y curl
LABEL dbw.extension="test_ext"
"""
    (ext_dir / "Dockerfile").write_text(dockerfile_content)

    return ext_dir


@pytest.fixture
def mock_docker_available():
    """Mock Docker availability."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def mock_git_operations():
    """Mock git operations."""
    with patch("git.Repo") as mock_repo_class:
        mock_repo = Mock()
        mock_repo.bare = True
        mock_repo.remotes.origin.fetch = Mock()
        mock_repo.git.worktree = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo_class.clone_from.return_value = mock_repo
        yield mock_repo


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def env_vars():
    """Set up test environment variables."""
    original_env = os.environ.copy()

    # Set test environment variables
    test_env = {
        "USER": "testuser",
        "HOME": "/home/testuser",
        "DISPLAY": ":0",
    }

    os.environ.update(test_env)

    yield test_env

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def mock_logging():
    """Mock logging to avoid noise in tests."""
    with patch("dbw.log.setup_logging"):
        yield


# Pytest configuration
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires Docker)"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")
