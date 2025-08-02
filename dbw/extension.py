"""Extension management for dbw."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests
from ruamel.yaml import YAML

from .config import get_extensions_dir, get_buildx_cache_dir
from .errors import ExtensionError, ExtensionInvalid
from .log import get_logger

logger = get_logger(__name__)

# Global YAML loader
yaml = YAML(typ="safe")


class ExtensionCache:
    """Manages extension cache and image building."""

    def __init__(self) -> None:
        self.extensions_dir = get_extensions_dir()
        self.cache_file = self.extensions_dir / "images.json"
        self.extensions_dir.mkdir(parents=True, exist_ok=True)

        # Load existing cache
        self._cache: dict[str, str] = {}
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("cache.load_failed", error=str(e))

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except OSError as e:
            logger.error("cache.save_failed", error=str(e))

    def _compute_hash(self, ext_dir: Path) -> str:
        """Compute SHA-256 hash of extension directory contents."""
        hasher = hashlib.sha256()

        # Hash all files in extension directory
        for file_path in sorted(ext_dir.rglob("*")):
            if file_path.is_file():
                hasher.update(file_path.name.encode())
                hasher.update(file_path.read_bytes())

        return hasher.hexdigest()

    def get_extension_path(self, name: str) -> Path:
        """Get path to extension directory."""
        return self.extensions_dir / name

    def list_extensions(self) -> list[str]:
        """List all cached extensions."""
        return [
            d.name
            for d in self.extensions_dir.iterdir()
            if d.is_dir() and (d / "docker-compose.fragment.yml").exists()
        ]

    def extension_exists(self, name: str) -> bool:
        """Check if extension exists in cache."""
        ext_path = self.get_extension_path(name)
        return ext_path.exists() and (ext_path / "docker-compose.fragment.yml").exists()

    def add_extension(self, name: str, source: str) -> None:
        """Add extension from URL or local path."""
        logger.info("extension.add", name=name, source=source)

        ext_path = self.get_extension_path(name)

        if source.startswith(("http://", "https://")):
            self._download_extension(name, source, ext_path)
        else:
            self._copy_extension(name, Path(source), ext_path)

        # Validate extension
        self._validate_extension(name)
        logger.info("extension.added", name=name)

    def _download_extension(self, name: str, url: str, ext_path: Path) -> None:  # pylint: disable=unused-argument
        """Download extension from URL."""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            ext_path.mkdir(parents=True, exist_ok=True)

            # Determine filename from URL
            parsed = urlparse(url)
            filename = Path(parsed.path).name or "docker-compose.fragment.yml"

            fragment_path = ext_path / filename
            fragment_path.write_text(response.text)

        except requests.RequestException as e:
            raise ExtensionError(f"Failed to download extension from {url}: {e}") from e

    def _copy_extension(self, name: str, source_path: Path, ext_path: Path) -> None:  # pylint: disable=unused-argument
        """Copy extension from local path."""
        if not source_path.exists():
            raise ExtensionError(f"Extension source not found: {source_path}")

        if ext_path.exists():
            shutil.rmtree(ext_path)

        if source_path.is_file():
            ext_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, ext_path / "docker-compose.fragment.yml")
        else:
            shutil.copytree(source_path, ext_path)

    def _validate_extension(self, name: str) -> None:
        """Validate extension YAML and Docker files."""
        ext_path = self.get_extension_path(name)
        fragment_path = ext_path / "docker-compose.fragment.yml"

        if not fragment_path.exists():
            raise ExtensionInvalid(f"Extension {name} missing docker-compose.fragment.yml")

        # Validate YAML syntax
        try:
            with open(fragment_path, encoding="utf-8") as f:
                fragment_data = yaml.load(f)
        except Exception as e:
            raise ExtensionInvalid(f"Invalid YAML in extension {name}: {e}") from e

        # Validate Docker Compose fragment syntax
        try:
            # Create temporary compose file to validate
            temp_compose = {
                "version": "3.8",
                "services": {
                    "dev": {
                        "image": "ubuntu:22.04",
                        "command": "sleep infinity",
                    }
                },
            }

            # Merge fragment
            if isinstance(fragment_data, dict) and "services" in fragment_data:
                if "dev" in fragment_data["services"]:
                    temp_compose["services"]["dev"].update(fragment_data["services"]["dev"])

            # Write and validate
            temp_file = ext_path / "temp-compose.yml"
            with open(temp_file, "w", encoding="utf-8") as f:
                yaml.dump(temp_compose, f)

            result = subprocess.run(
                ["docker", "compose", "-f", str(temp_file), "config"],
                capture_output=True,
                text=True,
                check=False,
            )

            temp_file.unlink(missing_ok=True)

            if result.returncode != 0:
                raise ExtensionInvalid(f"Invalid compose fragment in {name}: {result.stderr}")

        except FileNotFoundError:
            logger.warning("docker_compose_not_found", validation="skipped")

    def remove_extension(self, name: str) -> None:
        """Remove extension from cache."""
        logger.info("extension.remove", name=name)

        if not self.extension_exists(name):
            raise ExtensionError(f"Extension {name} not found")

        ext_path = self.get_extension_path(name)

        # Remove from cache
        hash_val = self._compute_hash(ext_path)
        if hash_val in self._cache:
            image_tag = self._cache[hash_val]
            del self._cache[hash_val]
            self._save_cache()

            # Remove Docker image if it exists
            try:
                subprocess.run(
                    ["docker", "rmi", image_tag],
                    capture_output=True,
                    check=False,
                )
            except Exception:
                pass  # Image might not exist

        # Remove directory
        shutil.rmtree(ext_path)
        logger.info("extension.removed", name=name)

    def get_extension_image(self, name: str, force_rebuild: bool = False) -> str:
        """Get or build extension image."""
        if not self.extension_exists(name):
            raise ExtensionError(f"Extension {name} not found")

        ext_path = self.get_extension_path(name)
        hash_val = self._compute_hash(ext_path)

        # Check cache hit
        if not force_rebuild and hash_val in self._cache:
            image_tag = self._cache[hash_val]
            logger.info("extension.cache_hit", name=name, image=image_tag)
            return image_tag

        # Build new image
        image_tag = f"dbw_ext_{name}:{hash_val[:12]}"
        self._build_extension_image(name, ext_path, image_tag)

        # Update cache
        self._cache[hash_val] = image_tag
        self._save_cache()

        return image_tag

    def _build_extension_image(self, name: str, ext_path: Path, image_tag: str) -> None:
        """Build extension image using Buildx."""
        logger.info("extension.build", name=name, image=image_tag)

        dockerfile_path = ext_path / "Dockerfile"
        if not dockerfile_path.exists():
            # Create minimal Dockerfile if none exists
            dockerfile_content = """FROM ubuntu:22.04
# Extension placeholder - add RUN commands in your Dockerfile
"""
            dockerfile_path.write_text(dockerfile_content)

        # Build with Buildx and cache
        cache_dir = get_buildx_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)

        build_cmd = [
            "docker",
            "buildx",
            "build",
            "--tag",
            image_tag,
            "--cache-from",
            f"type=local,src={cache_dir}",
            "--cache-to",
            f"type=local,dest={cache_dir},mode=max",
            "--build-arg",
            "BUILDKIT_INLINE_CACHE=1",
            "--load",
            str(ext_path),
        ]

        try:
            subprocess.run(
                build_cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("extension.built", name=name, image=image_tag)

        except subprocess.CalledProcessError as e:
            raise ExtensionError(f"Failed to build extension {name}: {e.stderr}") from e


def discover_repo_extensions(worktree_path: Path) -> list[str]:
    """Discover extensions defined in the repository."""
    extensions = []
    repo_ext_dir = worktree_path / ".dbw" / "extensions"

    if repo_ext_dir.exists():
        for ext_dir in repo_ext_dir.iterdir():
            if ext_dir.is_dir() and (ext_dir / "docker-compose.fragment.yml").exists():
                extensions.append(ext_dir.name)

                # Copy to global cache if not exists or different
                cache = ExtensionCache()
                if not cache.extension_exists(ext_dir.name):
                    cache.add_extension(ext_dir.name, str(ext_dir))
                    logger.info("repo_extension.cached", name=ext_dir.name)

    return extensions


def parse_extensions_list(extensions_str: str) -> list[str]:
    """Parse comma-separated extensions list."""
    if not extensions_str:
        return []

    return [ext.strip() for ext in extensions_str.split(",") if ext.strip()]


def validate_extensions(extensions: list[str]) -> None:
    """Validate that all extensions exist."""
    cache = ExtensionCache()
    missing = [ext for ext in extensions if not cache.extension_exists(ext)]

    if missing:
        available = cache.list_extensions()
        raise ExtensionError(
            f"Extensions not found: {missing}\n"
            f"Available: {available}\n"
            f"Use 'dbw ext add <name> <source>' to add missing extensions."
        )
