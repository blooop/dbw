"""Docker operations for dbw."""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from .errors import DockerError, DockerUnavailable
from .log import get_logger

logger = get_logger(__name__)


class DockerRunner:
    """Manages Docker operations for dbw."""
    
    def __init__(self, worktree_path: Path, project_name: str) -> None:
        self.worktree_path = worktree_path
        self.project_name = project_name
        self.compose_file = worktree_path / "docker-compose.yml"
    
    def check_docker_available(self) -> None:
        """Check if Docker daemon is available."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise DockerUnavailable(
                    "Docker daemon not running. Please start Docker and try again."
                )
        except FileNotFoundError:
            raise DockerUnavailable("Docker not found. Please install Docker.")
    
    def check_buildx_available(self) -> None:
        """Check if Docker Buildx is available."""
        try:
            result = subprocess.run(
                ["docker", "buildx", "version"],
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise DockerError("Docker Buildx not available. Please update Docker.")
        except FileNotFoundError:
            raise DockerError("Docker Buildx not found.")
    
    def check_compose_available(self) -> None:
        """Check if Docker Compose is available."""
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                raise DockerError("Docker Compose not available. Please install Docker Compose.")
        except FileNotFoundError:
            raise DockerError("Docker Compose not found.")
    
    def is_container_running(self) -> bool:
        """Check if the dev container is running."""
        container_name = f"{self.project_name}_dev"
        
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "-f", f"name={container_name}"],
                capture_output=True,
                text=True,
                check=False,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    def build_images(self, force_rebuild: bool = False) -> None:
        """Build or rebuild container images."""
        logger.info("docker.build", project=self.project_name, rebuild=force_rebuild)
        
        if not self.compose_file.exists():
            raise DockerError(f"Compose file not found: {self.compose_file}")
        
        cmd = ["docker", "compose", "-f", str(self.compose_file), "build"]
        
        if force_rebuild:
            cmd.append("--no-cache")
        
        try:
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = self.project_name
            
            subprocess.run(cmd, check=True, cwd=self.worktree_path, env=env)
            logger.info("docker.build_success")
            
        except subprocess.CalledProcessError as e:
            raise DockerError(f"Failed to build images: {e}")
    
    def start_container(self, detached: bool = True) -> None:
        """Start the development container."""
        logger.info("docker.start", project=self.project_name, detached=detached)
        
        if not self.compose_file.exists():
            raise DockerError(f"Compose file not found: {self.compose_file}")
        
        cmd = ["docker", "compose", "-f", str(self.compose_file), "up"]
        
        if detached:
            cmd.append("-d")
        
        try:
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = self.project_name
            
            subprocess.run(cmd, check=True, cwd=self.worktree_path, env=env)
            logger.info("docker.started")
            
        except subprocess.CalledProcessError as e:
            raise DockerError(f"Failed to start container: {e}")
    
    def exec_command(
        self,
        command: Optional[List[str]] = None,
        interactive: bool = True,
        service: str = "dev",
    ) -> int:
        """Execute command in container."""
        if not command:
            command = ["/bin/bash"]
        
        logger.info("docker.exec", project=self.project_name, command=command)
        
        if not self.is_container_running():
            raise DockerError(f"Container {self.project_name}_dev is not running")
        
        cmd = ["docker", "compose", "-f", str(self.compose_file), "exec"]
        
        if not interactive:
            cmd.append("-T")
        
        cmd.extend([service] + command)
        
        try:
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = self.project_name
            
            # For interactive sessions, pass through stdin/stdout/stderr
            if interactive:
                result = subprocess.run(cmd, cwd=self.worktree_path, env=env)
                return result.returncode
            else:
                result = subprocess.run(cmd, check=False, cwd=self.worktree_path, env=env)
                return result.returncode
                
        except subprocess.CalledProcessError as e:
            logger.error("docker.exec_failed", error=str(e))
            return e.returncode
        except KeyboardInterrupt:
            logger.info("docker.exec_interrupted")
            return 130  # SIGINT
    
    def stop_container(self) -> None:
        """Stop the development container."""
        logger.info("docker.stop", project=self.project_name)
        
        try:
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = self.project_name
            
            subprocess.run(
                ["docker", "compose", "-f", str(self.compose_file), "down"],
                check=False,  # Don't fail if already stopped
                cwd=self.worktree_path,
                env=env,
                capture_output=True,
            )
            logger.info("docker.stopped")
            
        except Exception as e:
            logger.warning("docker.stop_failed", error=str(e))
    
    def remove_container(self, remove_volumes: bool = False) -> None:
        """Remove the development container and optionally volumes."""
        logger.info("docker.remove", project=self.project_name, volumes=remove_volumes)
        
        try:
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = self.project_name
            
            cmd = ["docker", "compose", "-f", str(self.compose_file), "down"]
            
            if remove_volumes:
                cmd.extend(["--volumes", "--remove-orphans"])
            
            subprocess.run(
                cmd,
                check=False,
                cwd=self.worktree_path,
                env=env,
                capture_output=True,
            )
            logger.info("docker.removed")
            
        except Exception as e:
            logger.warning("docker.remove_failed", error=str(e))
    
    def get_container_logs(self, lines: int = 50) -> str:
        """Get container logs."""
        try:
            env = os.environ.copy()
            env["COMPOSE_PROJECT_NAME"] = self.project_name
            
            result = subprocess.run(
                ["docker", "compose", "-f", str(self.compose_file), "logs", "--tail", str(lines)],
                capture_output=True,
                text=True,
                cwd=self.worktree_path,
                env=env,
            )
            return result.stdout
            
        except Exception as e:
            logger.error("docker.logs_failed", error=str(e))
            return f"Failed to get logs: {e}"


def check_docker_socket() -> bool:
    """Check if Docker socket is available (for DOOD)."""
    socket_path = Path("/var/run/docker.sock")
    return socket_path.exists() and os.access(socket_path, os.R_OK | os.W_OK)


def check_nvidia_runtime() -> bool:
    """Check if NVIDIA Docker runtime is available."""
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.Runtimes}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "nvidia" in result.stdout
    except Exception:
        return False


def check_x11_available() -> bool:
    """Check if X11 is available for GUI forwarding."""
    display = os.environ.get("DISPLAY")
    if not display:
        return False
    
    x11_socket = Path("/tmp/.X11-unix")
    return x11_socket.exists()


def parse_command_args(args: List[str]) -> List[str]:
    """Parse command arguments, handling quoted strings."""
    if not args:
        return ["/bin/bash"]
    
    # If it's a single argument that looks like a compound command, use shell
    if len(args) == 1 and any(char in args[0] for char in [";", "&&", "||", "|"]):
        return ["/bin/bash", "-c", args[0]]
    
    return args