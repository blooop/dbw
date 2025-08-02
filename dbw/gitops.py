"""Git operations for dbw."""

import shutil
from pathlib import Path
from typing import Optional, Tuple

import git
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_workspaces_dir
from .errors import BranchMissing, DirtyWorktree, GitError, NetworkError
from .log import get_logger

logger = get_logger(__name__)


def parse_repo_spec(spec: str) -> Tuple[str, str, str, Optional[str]]:
    """Parse repo specification: owner/repo[@branch][#subfolder]

    Returns:
        (owner, repo, branch, subfolder)
    """
    # Split off subfolder if present
    if "#" in spec:
        spec, subfolder = spec.split("#", 1)
    else:
        subfolder = None

    # Split off branch if present
    if "@" in spec:
        repo_part, branch = spec.split("@", 1)
    else:
        repo_part, branch = spec, "main"

    # Split owner/repo
    if "/" not in repo_part:
        raise GitError(f"Invalid repo spec: {spec}. Must be owner/repo[@branch][#subfolder]")

    owner, repo = repo_part.split("/", 1)

    return owner, repo, branch, subfolder


def get_remote_url(owner: str, repo: str, use_ssh: bool = True) -> str:
    """Get remote URL for GitHub repo."""
    if use_ssh:
        return f"git@github.com:{owner}/{repo}.git"
    return f"https://github.com/{owner}/{repo}.git"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True,
)
def clone_repo(owner: str, repo: str, bare_path: Path) -> git.Repo:
    """Clone repository as bare repo with retries."""
    logger.info("clone.start", owner=owner, repo=repo, path=str(bare_path))

    try:
        # Only use SSH for cloning, do not fallback to HTTPS
        remote_url = get_remote_url(owner, repo, use_ssh=True)
        git_repo = git.Repo.clone_from(
            remote_url,
            bare_path,
            bare=True,
            progress=None,
        )
        logger.info("clone.success", path=str(bare_path))
        return git_repo

    except git.GitCommandError as e:
        if "Repository not found" in str(e) or "could not read" in str(e):
            raise NetworkError(f"Repository {owner}/{repo} not found or access denied") from e
        raise NetworkError(f"Failed to clone {owner}/{repo}: {e}") from e
    except OSError as e:
        if e.errno == 28:  # ENOSPC
            raise GitError(f"Not enough disk space to clone {owner}/{repo}") from e
        raise GitError(f"Failed to clone {owner}/{repo}: {e}") from e


def ensure_bare_repo(owner: str, repo: str) -> git.Repo:
    """Ensure bare repository exists, clone if needed."""
    workspaces_dir = get_workspaces_dir()
    bare_path = workspaces_dir / owner / repo

    if bare_path.exists():
        try:
            git_repo = git.Repo(bare_path)
            if not git_repo.bare:
                raise GitError(f"Repository at {bare_path} is not bare")

            # Ensure 'origin' remote exists
            if "origin" not in [remote.name for remote in git_repo.remotes]:
                git_repo.create_remote("origin", url=str(bare_path))

            # Fetch latest changes
            logger.info("fetch.start", path=str(bare_path))
            git_repo.remotes.origin.fetch(prune=True)
            logger.info("fetch.success")

            return git_repo

        except git.InvalidGitRepositoryError:
            logger.warning("corrupt_repo", path=str(bare_path), action="removing")
            shutil.rmtree(bare_path)

    # Clone if doesn't exist or was corrupted
    bare_path.parent.mkdir(parents=True, exist_ok=True)
    git_repo = clone_repo(owner, repo, bare_path)
    # Ensure 'origin' remote exists after clone
    if "origin" not in [remote.name for remote in git_repo.remotes]:
        git_repo.create_remote("origin", url=str(bare_path))
    return git_repo


def ensure_worktree(git_repo: git.Repo, repo: str, branch: str) -> Path:
    """Ensure worktree exists for branch."""
    bare_path = Path(git_repo.git_dir)
    worktree_path = bare_path.parent / f"{repo}-{branch}"

    logger.info("worktree.check", branch=branch, path=str(worktree_path))

    # Check if worktree already exists
    if worktree_path.exists():
        try:
            worktree_repo = git.Repo(worktree_path)

            # Check if worktree is dirty
            if worktree_repo.is_dirty(untracked_files=True):
                untracked = list(worktree_repo.untracked_files)
                modified = [item.a_path for item in worktree_repo.index.diff(None)]
                staged = [item.a_path for item in worktree_repo.index.diff("HEAD")]

                raise DirtyWorktree(
                    f"Worktree {worktree_path} has uncommitted changes:\n"
                    f"  Modified: {modified}\n"
                    f"  Staged: {staged}\n"
                    f"  Untracked: {untracked}\n"
                    f"Please commit or stash changes before switching."
                )

            logger.info("worktree.exists", path=str(worktree_path))
            return worktree_path

        except git.InvalidGitRepositoryError:
            logger.warning("invalid_worktree", path=str(worktree_path), action="removing")
            shutil.rmtree(worktree_path)

    # Create new worktree
    try:
        logger.info("worktree.create", branch=branch, path=str(worktree_path))

        # Check if branch exists remotely
        try:
            git_repo.remotes.origin.refs[branch]
        except (IndexError, KeyError) as exc:
            raise BranchMissing(f"Branch '{branch}' not found in remote repository") from exc

        # Add worktree
        git_repo.git.worktree("add", "-b", branch, str(worktree_path), f"origin/{branch}")
        logger.info("worktree.created", path=str(worktree_path))

        return worktree_path

    except git.GitCommandError as e:
        if "already exists" in str(e):
            # Branch exists locally, just add worktree
            git_repo.git.worktree("add", str(worktree_path), branch)
            return worktree_path
        raise GitError(f"Failed to create worktree for {branch}: {e}") from e


def get_compose_project_name(repo: str, branch: str) -> str:
    """Generate unique compose project name for repo/branch."""
    return f"dbw_{repo}_{branch}".replace("-", "_").replace(".", "_").lower()


def setup_worktree(owner: str, repo: str, branch: str) -> Tuple[Path, str]:
    """Setup complete worktree environment.

    Returns:
        (worktree_path, compose_project_name)
    """
    git_repo = ensure_bare_repo(owner, repo)
    worktree_path = ensure_worktree(git_repo, repo, branch)
    project_name = get_compose_project_name(repo, branch)

    logger.info(
        "worktree.ready",
        worktree=str(worktree_path),
        project=project_name,
    )

    return worktree_path, project_name
