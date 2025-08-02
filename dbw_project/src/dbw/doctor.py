"""System diagnostics for dbw."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, NamedTuple

from rich.console import Console
from rich.table import Table

from .config import get_buildx_cache_dir, get_workspaces_dir
from .log import get_logger

logger = get_logger(__name__)


class DiagnosticResult(NamedTuple):
    """Result of a diagnostic check."""
    name: str
    status: str  # "PASS", "WARN", "FAIL"
    message: str
    details: str = ""


class SystemDoctor:
    """System diagnostics and health checks."""
    
    def __init__(self) -> None:
        self.console = Console()
    
    def run_all_checks(self) -> List[DiagnosticResult]:
        """Run all diagnostic checks."""
        logger.info("doctor.start")
        
        checks = [
            self._check_docker_daemon,
            self._check_docker_compose,
            self._check_docker_buildx,
            self._check_disk_space,
            self._check_git,
            self._check_x11,
            self._check_nvidia_runtime,
            self._check_ssh_agent,
            self._check_directories,
            self._check_permissions,
        ]
        
        results = []
        for check in checks:
            try:
                result = check()
                results.append(result)
            except Exception as e:
                results.append(DiagnosticResult(
                    name=check.__name__.replace("_check_", "").replace("_", " ").title(),
                    status="FAIL",
                    message=f"Check failed: {e}",
                ))
        
        logger.info("doctor.complete", total=len(results))
        return results
    
    def print_results(self, results: List[DiagnosticResult]) -> None:
        """Print diagnostic results in a formatted table."""
        table = Table(title="DBW System Diagnostics")
        table.add_column("Check", style="bold")
        table.add_column("Status", justify="center")
        table.add_column("Message")
        
        for result in results:
            status_style = {
                "PASS": "green",
                "WARN": "yellow",
                "FAIL": "red",
            }.get(result.status, "white")
            
            table.add_row(
                result.name,
                f"[{status_style}]{result.status}[/{status_style}]",
                result.message,
            )
        
        self.console.print(table)
        
        # Print details for failed/warning checks
        for result in results:
            if result.status in ("FAIL", "WARN") and result.details:
                self.console.print(f"\n[bold]{result.name} Details:[/bold]")
                self.console.print(result.details)
    
    def _check_docker_daemon(self) -> DiagnosticResult:
        """Check if Docker daemon is running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                return DiagnosticResult(
                    name="Docker Daemon",
                    status="PASS",
                    message="Docker daemon is running",
                )
            else:
                return DiagnosticResult(
                    name="Docker Daemon",
                    status="FAIL",
                    message="Docker daemon not running",
                    details="Try: sudo systemctl start docker",
                )
        except FileNotFoundError:
            return DiagnosticResult(
                name="Docker Daemon",
                status="FAIL",
                message="Docker not installed",
                details="Install Docker: https://docs.docker.com/engine/install/",
            )
    
    def _check_docker_compose(self) -> DiagnosticResult:
        """Check Docker Compose availability."""
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                version = result.stdout.strip().split("\n")[0]
                return DiagnosticResult(
                    name="Docker Compose",
                    status="PASS",
                    message=f"Available: {version}",
                )
            else:
                return DiagnosticResult(
                    name="Docker Compose",
                    status="FAIL",
                    message="Docker Compose not available",
                )
        except FileNotFoundError:
            return DiagnosticResult(
                name="Docker Compose",
                status="FAIL",
                message="Docker Compose not found",
            )
    
    def _check_docker_buildx(self) -> DiagnosticResult:
        """Check Docker Buildx availability."""
        try:
            result = subprocess.run(
                ["docker", "buildx", "version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                version = result.stdout.strip().split("\n")[0]
                return DiagnosticResult(
                    name="Docker Buildx",
                    status="PASS",
                    message=f"Available: {version}",
                )
            else:
                return DiagnosticResult(
                    name="Docker Buildx",
                    status="FAIL",
                    message="Docker Buildx not available",
                )
        except FileNotFoundError:
            return DiagnosticResult(
                name="Docker Buildx",
                status="FAIL",
                message="Docker Buildx not found",
            )
    
    def _check_disk_space(self) -> DiagnosticResult:
        """Check available disk space."""
        workspaces_dir = get_workspaces_dir()
        cache_dir = get_buildx_cache_dir()
        
        try:
            # Check workspaces directory
            workspaces_stat = shutil.disk_usage(workspaces_dir.parent)
            workspaces_free_gb = workspaces_stat.free / (1024**3)
            
            # Check cache directory
            cache_stat = shutil.disk_usage(cache_dir.parent)
            cache_free_gb = cache_stat.free / (1024**3)
            
            min_free_gb = 5.0  # Minimum 5GB required
            
            if workspaces_free_gb < min_free_gb or cache_free_gb < min_free_gb:
                return DiagnosticResult(
                    name="Disk Space",
                    status="WARN",
                    message=f"Low disk space: {min(workspaces_free_gb, cache_free_gb):.1f}GB free",
                    details=f"Workspaces: {workspaces_free_gb:.1f}GB, Cache: {cache_free_gb:.1f}GB",
                )
            else:
                return DiagnosticResult(
                    name="Disk Space",
                    status="PASS",
                    message=f"Sufficient space: {min(workspaces_free_gb, cache_free_gb):.1f}GB free",
                )
        except Exception as e:
            return DiagnosticResult(
                name="Disk Space",
                status="FAIL",
                message=f"Failed to check disk space: {e}",
            )
    
    def _check_git(self) -> DiagnosticResult:
        """Check Git installation and version."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                # Check for minimum version (2.30+ for worktree improvements)
                version_parts = version.split()
                if len(version_parts) >= 3:
                    version_num = version_parts[2]
                    major, minor = map(int, version_num.split(".")[:2])
                    if major > 2 or (major == 2 and minor >= 30):
                        return DiagnosticResult(
                            name="Git",
                            status="PASS",
                            message=f"Available: {version}",
                        )
                    else:
                        return DiagnosticResult(
                            name="Git",
                            status="WARN",
                            message=f"Old version: {version}",
                            details="Recommend Git 2.30+ for best worktree support",
                        )
                return DiagnosticResult(
                    name="Git",
                    status="PASS",
                    message=f"Available: {version}",
                )
            else:
                return DiagnosticResult(
                    name="Git",
                    status="FAIL",
                    message="Git not working",
                )
        except FileNotFoundError:
            return DiagnosticResult(
                name="Git",
                status="FAIL",
                message="Git not installed",
            )
    
    def _check_x11(self) -> DiagnosticResult:
        """Check X11 availability for GUI forwarding."""
        display = os.environ.get("DISPLAY")
        if not display:
            return DiagnosticResult(
                name="X11 GUI",
                status="WARN",
                message="DISPLAY not set",
                details="GUI applications will not work",
            )
        
        x11_socket = Path("/tmp/.X11-unix")
        if not x11_socket.exists():
            return DiagnosticResult(
                name="X11 GUI",
                status="WARN",
                message="X11 socket not found",
                details="GUI applications may not work",
            )
        
        return DiagnosticResult(
            name="X11 GUI",
            status="PASS",
            message=f"Available: {display}",
        )
    
    def _check_nvidia_runtime(self) -> DiagnosticResult:
        """Check NVIDIA Docker runtime availability."""
        try:
            result = subprocess.run(
                ["docker", "info", "--format", "{{.Runtimes}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and "nvidia" in result.stdout:
                return DiagnosticResult(
                    name="NVIDIA GPU",
                    status="PASS",
                    message="NVIDIA runtime available",
                )
            else:
                return DiagnosticResult(
                    name="NVIDIA GPU",
                    status="WARN",
                    message="NVIDIA runtime not available",
                    details="GPU acceleration will not work",
                )
        except Exception:
            return DiagnosticResult(
                name="NVIDIA GPU",
                status="WARN",
                message="Cannot check NVIDIA runtime",
            )
    
    def _check_ssh_agent(self) -> DiagnosticResult:
        """Check SSH agent availability."""
        ssh_auth_sock = os.environ.get("SSH_AUTH_SOCK")
        if not ssh_auth_sock:
            return DiagnosticResult(
                name="SSH Agent",
                status="WARN",
                message="SSH_AUTH_SOCK not set",
                details="SSH key forwarding will not work",
            )
        
        if not Path(ssh_auth_sock).exists():
            return DiagnosticResult(
                name="SSH Agent",
                status="WARN",
                message="SSH agent socket not found",
                details="SSH key forwarding will not work",
            )
        
        return DiagnosticResult(
            name="SSH Agent",
            status="PASS",
            message="SSH agent available",
        )
    
    def _check_directories(self) -> DiagnosticResult:
        """Check if required directories exist and are writable."""
        dirs_to_check = [
            get_workspaces_dir(),
            get_buildx_cache_dir(),
        ]
        
        for dir_path in dirs_to_check:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                if not os.access(dir_path, os.W_OK):
                    return DiagnosticResult(
                        name="Directories",
                        status="FAIL",
                        message=f"Directory not writable: {dir_path}",
                    )
            except Exception as e:
                return DiagnosticResult(
                    name="Directories",
                    status="FAIL",
                    message=f"Cannot create directory: {dir_path}",
                    details=str(e),
                )
        
        return DiagnosticResult(
            name="Directories",
            status="PASS",
            message="All directories accessible",
        )
    
    def _check_permissions(self) -> DiagnosticResult:
        """Check Docker permissions and group membership."""
        try:
            # Check if user can run docker without sudo
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                check=False,
            )
            if result.returncode == 0:
                return DiagnosticResult(
                    name="Docker Permissions",
                    status="PASS",
                    message="Docker accessible without sudo",
                )
            else:
                return DiagnosticResult(
                    name="Docker Permissions",
                    status="WARN",
                    message="Docker requires sudo",
                    details="Add user to docker group: sudo usermod -aG docker $USER",
                )
        except Exception as e:
            return DiagnosticResult(
                name="Docker Permissions",
                status="FAIL",
                message=f"Cannot check Docker permissions: {e}",
            )


def run_doctor() -> int:
    """Run system diagnostics and return exit code."""
    doctor = SystemDoctor()
    results = doctor.run_all_checks()
    doctor.print_results(results)
    
    # Return non-zero if any critical checks failed
    critical_failures = [r for r in results if r.status == "FAIL"]
    if critical_failures:
        logger.error("doctor.critical_failures", count=len(critical_failures))
        return 1
    
    warnings = [r for r in results if r.status == "WARN"]
    if warnings:
        logger.warning("doctor.warnings", count=len(warnings))
    
    return 0