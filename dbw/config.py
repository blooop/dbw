"""Configuration management for dbw."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


# XDG Base Directory paths
def get_data_home() -> Path:
    """Get XDG data home directory."""
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def get_config_home() -> Path:
    """Get XDG config home directory."""
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def get_cache_home() -> Path:
    """Get XDG cache home directory."""
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))


# Default paths
DBW_DATA_DIR = get_data_home() / "dbw"
DBW_CONFIG_DIR = get_config_home() / "dbw"
DBW_CACHE_DIR = get_cache_home() / "dbw"

WORKSPACES_DIR = DBW_DATA_DIR / "workspaces"
EXTENSIONS_DIR = DBW_DATA_DIR / "extensions"
LOGS_DIR = DBW_DATA_DIR / "logs"
BUILDX_CACHE_DIR = DBW_CACHE_DIR / "buildx"

# Environment variable defaults
ENV_DEFAULTS = {
    "DBW_DATA_DIR": str(DBW_DATA_DIR),
    "DBW_CONFIG_DIR": str(DBW_CONFIG_DIR),
    "DBW_CACHE_DIR": str(DBW_CACHE_DIR),
    "DBW_WORKSPACES_DIR": str(WORKSPACES_DIR),
    "DBW_EXTENSIONS_DIR": str(EXTENSIONS_DIR),
    "DBW_LOGS_DIR": str(LOGS_DIR),
    "DBW_BUILDX_CACHE_DIR": str(BUILDX_CACHE_DIR),
    "DBW_BASE_IMAGE": "dbw/ubuntu-base:latest",
    "DBW_CACHE_REGISTRY": "",  # Empty = use local cache only
    "DBW_BUILDX_BUILDER": "dbw_builder",
    "DBW_COMPOSE_PROJECT_PREFIX": "dbw",
}

# Docker constants
DOCKER_SOCKET_PATH = Path("/var/run/docker.sock")
DOCKERFILE_BASE = "Dockerfile"
COMPOSE_BASE = "docker-compose.yml"
BAKE_FILE = "docker-bake.hcl"


class RepoConfig(BaseModel):
    """Configuration loaded from .dbw.yml in repository."""

    extensions: list[str] = Field(default_factory=list)
    subfolder: Optional[str] = None
    platforms: list[str] = Field(default_factory=lambda: ["linux/amd64"])
    base_image: Optional[str] = None
    env: dict[str, str] = Field(default_factory=dict)
    volumes: list[str] = Field(default_factory=list)
    ports: list[str] = Field(default_factory=list)


class CacheConfig(BaseModel):
    """Buildx cache configuration."""

    type: str = "local"  # local, registry, inline
    registry_ref: Optional[str] = None
    local_dir: Optional[str] = None
    mode: str = "max"


class DbwConfig(BaseModel):
    """Global dbw configuration."""

    base_image: str = ENV_DEFAULTS["DBW_BASE_IMAGE"]
    cache: CacheConfig = Field(default_factory=CacheConfig)
    builder_name: str = ENV_DEFAULTS["DBW_BUILDX_BUILDER"]
    auto_gpu: bool = True
    auto_x11: bool = True


def ensure_dirs() -> None:
    """Ensure all required directories exist."""
    dirs = [
        DBW_DATA_DIR,
        DBW_CONFIG_DIR,
        DBW_CACHE_DIR,
        WORKSPACES_DIR,
        EXTENSIONS_DIR,
        LOGS_DIR,
        BUILDX_CACHE_DIR,
    ]
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)


def get_env(key: str, default: Optional[str] = None) -> str:
    """Get environment variable with default."""
    return os.environ.get(key, default or ENV_DEFAULTS.get(key, ""))


def get_workspaces_dir() -> Path:
    """Get workspaces directory from env or default."""
    return Path(get_env("DBW_WORKSPACES_DIR"))


def get_extensions_dir() -> Path:
    """Get extensions directory from env or default."""
    return Path(get_env("DBW_EXTENSIONS_DIR"))


def get_logs_dir() -> Path:
    """Get logs directory from env or default."""
    return Path(get_env("DBW_LOGS_DIR"))


def get_buildx_cache_dir() -> Path:
    """Get buildx cache directory from env or default."""
    return Path(get_env("DBW_BUILDX_CACHE_DIR"))
