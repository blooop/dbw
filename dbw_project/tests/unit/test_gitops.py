"""Unit tests for dbw.gitops module."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from dbw.gitops import (
    parse_repo_spec,
    get_remote_url,
    get_compose_project_name,
    setup_worktree,
)
from dbw.errors import GitError, BranchMissing, DirtyWorktree


class TestParseRepoSpec:
    """Test repository specification parsing."""
    
    def test_basic_spec(self):
        """Test basic owner/repo format."""
        owner, repo, branch, subfolder = parse_repo_spec("user/repo")
        assert owner == "user"
        assert repo == "repo"
        assert branch == "main"
        assert subfolder is None
    
    def test_spec_with_branch(self):
        """Test owner/repo@branch format."""
        owner, repo, branch, subfolder = parse_repo_spec("user/repo@feature")
        assert owner == "user"
        assert repo == "repo"
        assert branch == "feature"
        assert subfolder is None
    
    def test_spec_with_subfolder(self):
        """Test owner/repo#subfolder format."""
        owner, repo, branch, subfolder = parse_repo_spec("user/repo#src")
        assert owner == "user"
        assert repo == "repo"
        assert branch == "main"
        assert subfolder == "src"
    
    def test_spec_with_branch_and_subfolder(self):
        """Test owner/repo@branch#subfolder format."""
        owner, repo, branch, subfolder = parse_repo_spec("user/repo@dev#docs")
        assert owner == "user"
        assert repo == "repo"
        assert branch == "dev"
        assert subfolder == "docs"
    
    def test_invalid_spec_no_slash(self):
        """Test invalid spec without slash."""
        with pytest.raises(GitError, match="Invalid repo spec"):
            parse_repo_spec("invalid")
    
    def test_invalid_spec_empty(self):
        """Test empty spec."""
        with pytest.raises(GitError, match="Invalid repo spec"):
            parse_repo_spec("")


class TestGetRemoteUrl:
    """Test remote URL generation."""
    
    def test_ssh_url(self):
        """Test SSH URL generation."""
        url = get_remote_url("user", "repo", use_ssh=True)
        assert url == "git@github.com:user/repo.git"
    
    def test_https_url(self):
        """Test HTTPS URL generation."""
        url = get_remote_url("user", "repo", use_ssh=False)
        assert url == "https://github.com/user/repo.git"


class TestComposeProjectName:
    """Test compose project name generation."""
    
    def test_basic_name(self):
        """Test basic project name."""
        name = get_compose_project_name("repo", "main")
        assert name == "dbw_repo_main"
    
    def test_name_with_dashes(self):
        """Test project name with dashes."""
        name = get_compose_project_name("my-repo", "feature-branch")
        assert name == "dbw_my_repo_feature_branch"
    
    def test_name_with_dots(self):
        """Test project name with dots."""
        name = get_compose_project_name("repo.test", "v1.0")
        assert name == "dbw_repo_test_v1_0"


class TestSetupWorktree:
    """Test worktree setup functionality."""
    
    @patch("dbw.gitops.ensure_bare_repo")
    @patch("dbw.gitops.ensure_worktree")
    def test_setup_worktree_success(self, mock_ensure_worktree, mock_ensure_bare_repo):
        """Test successful worktree setup."""
        # Mock return values
        mock_repo = Mock()
        mock_ensure_bare_repo.return_value = mock_repo
        mock_ensure_worktree.return_value = Path("/test/repo-main")
        
        worktree_path, project_name = setup_worktree("user", "repo", "main")
        
        # Verify calls
        mock_ensure_bare_repo.assert_called_once_with("user", "repo")
        mock_ensure_worktree.assert_called_once_with(mock_repo, "repo", "main")
        
        # Verify results
        assert worktree_path == Path("/test/repo-main")
        assert project_name == "dbw_repo_main"


@patch("dbw.gitops.clone_repo")
@patch("dbw.gitops.get_workspaces_dir")
class TestEnsureBareRepo:
    """Test bare repository management."""
    
    def test_existing_repo_fetch(self, mock_get_workspaces_dir, mock_clone_repo):
        """Test fetching updates for existing repo."""
        from dbw.gitops import ensure_bare_repo
        
        # Setup mocks
        workspaces_dir = Path("/test/workspaces")
        mock_get_workspaces_dir.return_value = workspaces_dir
        
        repo_path = workspaces_dir / "user" / "repo"
        
        with patch("pathlib.Path.exists", return_value=True):
            with patch("git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo.bare = True
                mock_repo.remotes.origin.fetch = Mock()
                mock_repo_class.return_value = mock_repo
                
                result = ensure_bare_repo("user", "repo")
                
                # Verify repo was loaded and fetched
                mock_repo_class.assert_called_once_with(repo_path)
                mock_repo.remotes.origin.fetch.assert_called_once_with(prune=True)
                assert result == mock_repo
    
    def test_new_repo_clone(self, mock_get_workspaces_dir, mock_clone_repo):
        """Test cloning new repository."""
        from dbw.gitops import ensure_bare_repo
        
        # Setup mocks
        workspaces_dir = Path("/test/workspaces")
        mock_get_workspaces_dir.return_value = workspaces_dir
        
        repo_path = workspaces_dir / "user" / "repo"
        mock_repo = Mock()
        mock_clone_repo.return_value = mock_repo
        
        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.mkdir"):
                result = ensure_bare_repo("user", "repo")
                
                # Verify clone was called
                mock_clone_repo.assert_called_once_with("user", "repo", repo_path)
                assert result == mock_repo


@patch("dbw.gitops.git.Repo")
class TestEnsureWorktree:
    """Test worktree management."""
    
    def test_existing_clean_worktree(self, mock_repo_class):
        """Test using existing clean worktree."""
        from dbw.gitops import ensure_worktree
        
        # Setup mocks
        mock_bare_repo = Mock()
        mock_bare_repo.git_dir = "/test/repo.git"
        
        worktree_path = Path("/test/repo-main")
        
        with patch("pathlib.Path.exists", return_value=True):
            mock_worktree_repo = Mock()
            mock_worktree_repo.is_dirty.return_value = False
            mock_repo_class.return_value = mock_worktree_repo
            
            result = ensure_worktree(mock_bare_repo, "repo", "main")
            
            assert result == worktree_path
            mock_worktree_repo.is_dirty.assert_called_once_with(untracked_files=True)
    
    def test_dirty_worktree_error(self, mock_repo_class):
        """Test error on dirty worktree."""
        from dbw.gitops import ensure_worktree
        
        # Setup mocks
        mock_bare_repo = Mock()
        mock_bare_repo.git_dir = "/test/repo.git"
        
        with patch("pathlib.Path.exists", return_value=True):
            mock_worktree_repo = Mock()
            mock_worktree_repo.is_dirty.return_value = True
            mock_worktree_repo.untracked_files = ["file1.txt"]
            mock_worktree_repo.index.diff.return_value = []
            mock_repo_class.return_value = mock_worktree_repo
            
            with pytest.raises(DirtyWorktree):
                ensure_worktree(mock_bare_repo, "repo", "main")
    
    def test_create_new_worktree(self, mock_repo_class):
        """Test creating new worktree."""
        from dbw.gitops import ensure_worktree
        
        # Setup mocks
        mock_bare_repo = Mock()
        mock_bare_repo.git_dir = "/test/repo.git"
        mock_bare_repo.remotes.origin.refs = {"main": Mock()}
        mock_bare_repo.git.worktree = Mock()
        
        worktree_path = Path("/test/repo-main")
        
        with patch("pathlib.Path.exists", return_value=False):
            result = ensure_worktree(mock_bare_repo, "repo", "main")
            
            # Verify worktree was created
            mock_bare_repo.git.worktree.assert_called_once_with(
                "add", "-b", "main", str(worktree_path), "origin/main"
            )
            assert result == worktree_path
    
    def test_missing_branch_error(self, mock_repo_class):
        """Test error when branch doesn't exist."""
        from dbw.gitops import ensure_worktree
        
        # Setup mocks
        mock_bare_repo = Mock()
        mock_bare_repo.git_dir = "/test/repo.git"
        mock_bare_repo.remotes.origin.refs = {}  # No branches
        
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(BranchMissing, match="Branch 'nonexistent' not found"):
                ensure_worktree(mock_bare_repo, "repo", "nonexistent")