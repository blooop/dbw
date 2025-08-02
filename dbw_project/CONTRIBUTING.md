# Contributing to DBW

We welcome contributions to DBW! This document provides guidelines for contributing to the project.

## Getting Started

### Development Environment

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/dbw.git
   cd dbw
   ```

2. **Set up development environment**
   ```bash
   # Install Poetry if you haven't already
   curl -sSL https://install.python-poetry.org | python3 -

   # Install dependencies
   poetry install --with dev

   # Activate virtual environment
   poetry shell
   ```

3. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

4. **Verify setup**
   ```bash
   # Run tests
   pytest

   # Check code style
   black --check .
   ruff check .
   mypy src/dbw
   ```

### Project Structure

```
dbw/
├── src/dbw/              # Main package
│   ├── cli.py            # CLI interface
│   ├── gitops.py         # Git worktree operations
│   ├── extension.py      # Extension management
│   ├── compose.py        # Docker Compose generation
│   ├── docker_runner.py  # Docker operations
│   └── ...
├── templates/            # Docker templates
├── extensions/           # Built-in extensions
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── scripts/             # Utility scripts
└── docs/                # Documentation
```

## Development Workflow

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Run unit tests
   pytest tests/unit

   # Run integration tests (requires Docker)
   pytest tests/integration

   # Run all tests
   pytest

   # Check code coverage
   pytest --cov=src/dbw --cov-report=html
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix  
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add support for custom base images
fix: handle missing docker socket gracefully
docs: update installation instructions
test: add unit tests for extension cache
```

## Coding Standards

### Python Code Style

- **Formatting**: Use [Black](https://black.readthedocs.io/)
- **Linting**: Use [Ruff](https://docs.astral.sh/ruff/)
- **Type Checking**: Use [mypy](https://mypy.readthedocs.io/) with strict mode
- **Docstrings**: Use Google-style docstrings

### Code Quality Guidelines

1. **Type Hints**: All public functions should have type hints
   ```python
   def setup_worktree(owner: str, repo: str, branch: str) -> Tuple[Path, str]:
       """Setup git worktree for repository branch."""
   ```

2. **Error Handling**: Use custom exceptions from `dbw.errors`
   ```python
   from dbw.errors import GitError
   
   if not branch_exists:
       raise GitError(f"Branch '{branch}' not found")
   ```

3. **Logging**: Use structured logging
   ```python
   from dbw.log import get_logger
   
   logger = get_logger(__name__)
   logger.info("worktree.created", path=str(worktree_path))
   ```

4. **Testing**: Aim for >90% test coverage
   - Unit tests for business logic
   - Integration tests for Docker operations
   - Mock external dependencies

### Docker Best Practices

1. **Multi-stage builds** for extensions when appropriate
2. **Cache-friendly layers** - put changing content last
3. **Security** - run as non-root user, minimal attack surface
4. **Labels** - include `dbw.extension` and `dbw.version` labels

## Testing

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - Fast, isolated tests
   - Mock external dependencies
   - Test business logic

2. **Integration Tests** (`tests/integration/`)
   - Test Docker integration
   - Require Docker daemon
   - Test end-to-end workflows

### Writing Tests

```python
# Unit test example
def test_parse_repo_spec():
    """Test repository specification parsing."""
    owner, repo, branch, subfolder = parse_repo_spec("user/repo@main#src")
    assert owner == "user"
    assert repo == "repo"
    assert branch == "main"
    assert subfolder == "src"

# Integration test example
@pytest.mark.integration
def test_docker_container_launch(tmp_path):
    """Test launching Docker container."""
    # Test requires Docker daemon
    pass
```

### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit

# Run only integration tests (requires Docker)
pytest tests/integration

# Run with coverage
pytest --cov=src/dbw

# Run specific test
pytest tests/unit/test_gitops.py::test_parse_repo_spec
```

## Documentation

### Types of Documentation

1. **Code Documentation**
   - Docstrings for all public functions/classes
   - Type hints for all public APIs
   - Comments for complex logic

2. **User Documentation**
   - README.md - getting started guide
   - CLI help text - accessible via `dbw --help`
   - Extension documentation

3. **Developer Documentation**
   - This CONTRIBUTING.md file
   - Architecture documentation
   - API documentation

### Documentation Standards

- Use clear, concise language
- Include code examples
- Keep documentation up-to-date with code changes
- Use proper Markdown formatting

## Creating Extensions

### Extension Structure

```
extension_name/
├── docker-compose.fragment.yml  # Required: Compose fragment
├── Dockerfile                   # Optional: Custom image
└── README.md                   # Optional: Documentation
```

### Extension Guidelines

1. **Compose Fragment** should only extend the `dev` service:
   ```yaml
   version: '3.8'
   services:
     dev:
       environment:
         TOOL_CONFIG: /workspace/.tool
       volumes:
         - tool_cache:/home/dev/.cache/tool
   volumes:
     tool_cache:
   ```

2. **Dockerfile** should:
   - Use Ubuntu 22.04 base (or build on `dbw/ubuntu-base`)
   - Install tools efficiently (minimal layers)
   - Include proper labels
   - Create setup scripts for shell integration

3. **Testing** extensions:
   ```bash
   # Validate compose fragment
   docker compose -f docker-compose.fragment.yml config
   
   # Test build
   docker build -t test-ext .
   
   # Test in DBW
   dbw ext add test-ext .
   dbw launch test/repo@main --with test-ext
   ```

## Pull Request Process

### Before Submitting

1. **Check that tests pass**
   ```bash
   pytest
   ```

2. **Check code style**
   ```bash
   black --check .
   ruff check .
   mypy src/dbw
   ```

3. **Update documentation** if needed

4. **Add entry to CHANGELOG.md** if appropriate

### Pull Request Template

When creating a PR, please include:

- **Description**: What does this PR do?
- **Motivation**: Why is this change needed?
- **Testing**: How was this tested?
- **Breaking Changes**: Any breaking changes?
- **Checklist**:
  - [ ] Tests pass
  - [ ] Code follows style guidelines
  - [ ] Documentation updated
  - [ ] Changelog updated (if applicable)

### Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **Code review** by at least one maintainer
3. **Manual testing** of new features when appropriate
4. **Documentation review** for user-facing changes

## Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md**
3. **Create release tag**
   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```
4. **GitHub Actions** handles the rest:
   - Run tests
   - Build and publish to PyPI
   - Build and publish Docker images
   - Create GitHub release

## Getting Help

### Communication Channels

- **GitHub Issues** - Bug reports, feature requests
- **GitHub Discussions** - Questions, ideas, community chat
- **GitHub Pull Requests** - Code review, collaboration

### Issue Templates

When reporting bugs, please include:
- DBW version (`dbw --version`)
- Python version
- Operating system
- Docker version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs

### Feature Requests

When requesting features, please include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Additional context

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/). By participating, you are expected to uphold this code.

### Our Standards

- Be welcoming and inclusive
- Be respectful of different viewpoints
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards other community members

## License

By contributing to DBW, you agree that your contributions will be licensed under the MIT License.