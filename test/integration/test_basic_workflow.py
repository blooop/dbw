# Typer-based CLI tests removed. CLI is now direct, not Typer app.
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
