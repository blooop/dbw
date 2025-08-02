"""Integration tests for basic dbw workflow."""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch

from dbw.cli import app
from typer.testing import CliRunner


@pytest.mark.integration
class TestBasicWorkflow:
    """Test basic dbw workflow integration."""

    def test_cli_version(self):
        """Test CLI version command."""
        runner = CliRunner()
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "dbw" in result.stdout

    def test_cli_help(self):
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Docker Buildx/Bake Worktree" in result.stdout

    def test_doctor_command(self):
        """Test doctor command."""
        runner = CliRunner()
        with patch("dbw.doctor.run_doctor", return_value=0):
            result = runner.invoke(app, ["doctor"])
            assert result.exit_code == 0

    def test_ext_list_empty(self):
        """Test listing extensions when none are available."""
        runner = CliRunner()
        with patch("dbw.cli.ExtensionCache") as mock_cache_class:
            mock_cache = mock_cache_class.return_value
            mock_cache.list_extensions.return_value = []

            result = runner.invoke(app, ["ext", "list"])
            assert result.exit_code == 0
            assert "No extensions found" in result.stdout

    def test_ext_list_with_extensions(self):
        """Test listing extensions when some are available."""
        runner = CliRunner()
        with patch("dbw.cli.ExtensionCache") as mock_cache_class:
            mock_cache = mock_cache_class.return_value
            mock_cache.list_extensions.return_value = ["fzf", "uv"]
            mock_cache.get_extension_path.side_effect = lambda name: Path(f"/test/{name}")

            result = runner.invoke(app, ["ext", "list"])
            assert result.exit_code == 0
            assert "fzf" in result.stdout
            assert "uv" in result.stdout

    @patch("dbw.cli.setup_worktree")
    @patch("dbw.cli.DockerRunner")
    def test_launch_command_attach_existing(self, mock_docker_runner_class, mock_setup_worktree):
        """Test launch command when container already exists."""
        runner = CliRunner()

        # Mock setup
        mock_setup_worktree.return_value = (Path("/test/worktree"), "test_project")
        mock_runner = mock_docker_runner_class.return_value
        mock_runner.is_container_running.return_value = True
        mock_runner.exec_command.return_value = 0

        with (
            patch("dbw.cli.load_repo_config"),
            patch("dbw.cli.discover_repo_extensions", return_value=[]),
            patch("dbw.cli.get_working_directory", return_value=Path("/test/worktree")),
        ):
            result = runner.invoke(app, ["launch", "test/repo@main"])

            # Should attach to existing container
            mock_runner.exec_command.assert_called_once()
            assert result.exit_code == 0

    @patch("dbw.cli.setup_worktree")
    @patch("dbw.cli.DockerRunner")
    def test_launch_command_new_container(self, mock_docker_runner_class, mock_setup_worktree):
        """Test launch command creating new container."""
        runner = CliRunner()

        # Mock setup
        mock_setup_worktree.return_value = (Path("/test/worktree"), "test_project")
        mock_runner = mock_docker_runner_class.return_value
        mock_runner.is_container_running.return_value = False
        mock_runner.build_images = lambda force_rebuild: None
        mock_runner.start_container = lambda: None
        mock_runner.exec_command.return_value = 0

        with (
            patch("dbw.cli.load_repo_config"),
            patch("dbw.cli.discover_repo_extensions", return_value=[]),
            patch("dbw.cli.get_working_directory", return_value=Path("/test/worktree")),
            patch("dbw.cli.create_base_dockerfile"),
            patch("dbw.cli.generate_compose_file"),
        ):
            result = runner.invoke(app, ["launch", "test/repo@main"])

            # Should build and start new container
            assert result.exit_code == 0

    def test_launch_invalid_spec(self):
        """Test launch command with invalid repo spec."""
        runner = CliRunner()
        result = runner.invoke(app, ["launch", "invalid-spec"])
        assert result.exit_code != 0
        assert "Invalid repo spec" in result.stdout

    @patch("dbw.cli.setup_worktree")
    @patch("dbw.cli.DockerRunner")
    def test_destroy_command(self, mock_docker_runner_class, mock_setup_worktree):
        """Test destroy command."""
        runner = CliRunner()

        # Mock setup
        mock_setup_worktree.return_value = (Path("/test/worktree"), "test_project")
        mock_runner = mock_docker_runner_class.return_value
        mock_runner.remove_container = lambda remove_volumes: None

        result = runner.invoke(app, ["destroy", "test/repo@main"])
        assert result.exit_code == 0
        assert "destroyed" in result.stdout.lower()

    def test_list_command_no_containers(self):
        """Test list command when no containers are running."""
        runner = CliRunner()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout="", stderr=""
            )

            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "No active environments" in result.stdout

    def test_list_command_with_containers(self):
        """Test list command with running containers."""
        runner = CliRunner()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [],
                returncode=0,
                stdout="NAMES\tSTATUS\tPORTS\ndbw_test_main_dev\tUp 2 minutes\t",
                stderr="",
            )

            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            assert "dbw_test_main_dev" in result.stdout

    def test_prune_command_cancelled(self):
        """Test prune command when user cancels."""
        runner = CliRunner()

        # Simulate user input 'n' (no)
        result = runner.invoke(app, ["prune"], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.stdout

    def test_prune_command_forced(self):
        """Test prune command with force flag."""
        runner = CliRunner()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], returncode=0)

            result = runner.invoke(app, ["prune", "--force"])
            assert result.exit_code == 0
            assert "Cleanup complete" in result.stdout

    def test_update_command(self):
        """Test update command."""
        runner = CliRunner()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], returncode=0)

            result = runner.invoke(app, ["update"])
            assert result.exit_code == 0
            assert "Update complete" in result.stdout


@pytest.mark.integration
@pytest.mark.slow
class TestDockerIntegration:
    """Test actual Docker integration (requires Docker)."""

    def test_docker_available(self):
        """Test that Docker is available for integration tests."""
        try:
            result = subprocess.run(["docker", "info"], capture_output=True, check=True, timeout=10)
            assert result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Docker not available for integration tests")

    def test_buildx_available(self):
        """Test that Docker Buildx is available."""
        try:
            result = subprocess.run(
                ["docker", "buildx", "version"], capture_output=True, check=True, timeout=10
            )
            assert result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Docker Buildx not available for integration tests")

    def test_compose_available(self):
        """Test that Docker Compose is available."""
        try:
            result = subprocess.run(
                ["docker", "compose", "version"], capture_output=True, check=True, timeout=10
            )
            assert result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pytest.skip("Docker Compose not available for integration tests")
