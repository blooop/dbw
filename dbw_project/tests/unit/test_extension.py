"""Unit tests for dbw.extension module."""

import json
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from dbw.extension import (
    ExtensionCache,
    discover_repo_extensions,
    parse_extensions_list,
    validate_extensions,
)
from dbw.errors import ExtensionError, ExtensionInvalid


class TestExtensionCache:
    """Test ExtensionCache functionality."""
    
    def test_init_creates_directories(self, mock_extensions_dir):
        """Test that cache initialization creates necessary directories."""
        cache = ExtensionCache()
        assert cache.extensions_dir == mock_extensions_dir
        assert mock_extensions_dir.exists()
    
    def test_init_loads_existing_cache(self, mock_extensions_dir):
        """Test loading existing cache file."""
        cache_data = {"hash123": "image:tag"}
        cache_file = mock_extensions_dir / "images.json"
        cache_file.write_text(json.dumps(cache_data))
        
        cache = ExtensionCache()
        assert cache._cache == cache_data
    
    def test_init_handles_invalid_cache(self, mock_extensions_dir):
        """Test handling invalid cache file."""
        cache_file = mock_extensions_dir / "images.json"
        cache_file.write_text("invalid json")
        
        # Should not raise, just start with empty cache
        cache = ExtensionCache()
        assert cache._cache == {}
    
    def test_list_extensions(self, extension_cache, sample_extension):
        """Test listing available extensions."""
        extensions = extension_cache.list_extensions()
        assert "test_ext" in extensions
    
    def test_extension_exists(self, extension_cache, sample_extension):
        """Test checking if extension exists."""
        assert extension_cache.extension_exists("test_ext")
        assert not extension_cache.extension_exists("nonexistent")
    
    def test_compute_hash(self, extension_cache, sample_extension):
        """Test hash computation for extension."""
        hash1 = extension_cache._compute_hash(sample_extension)
        hash2 = extension_cache._compute_hash(sample_extension)
        
        # Hash should be consistent
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256
        
        # Modify file and check hash changes
        (sample_extension / "new_file.txt").write_text("content")
        hash3 = extension_cache._compute_hash(sample_extension)
        assert hash1 != hash3
    
    @patch("subprocess.run")
    def test_validate_extension_success(self, mock_run, extension_cache, sample_extension):
        """Test successful extension validation."""
        mock_run.return_value = Mock(returncode=0)
        
        # Should not raise
        extension_cache._validate_extension("test_ext")
        
        # Should call docker compose config
        mock_run.assert_called()
        args = mock_run.call_args[0][0]
        assert "docker" in args
        assert "compose" in args
        assert "config" in args
    
    def test_validate_extension_missing_fragment(self, extension_cache, mock_extensions_dir):
        """Test validation failure for missing fragment."""
        ext_dir = mock_extensions_dir / "no_fragment"
        ext_dir.mkdir()
        
        with pytest.raises(ExtensionInvalid, match="missing docker-compose.fragment.yml"):
            extension_cache._validate_extension("no_fragment")
    
    def test_validate_extension_invalid_yaml(self, extension_cache, mock_extensions_dir):
        """Test validation failure for invalid YAML."""
        ext_dir = mock_extensions_dir / "invalid_yaml"
        ext_dir.mkdir()
        
        # Create invalid YAML
        fragment_file = ext_dir / "docker-compose.fragment.yml"
        fragment_file.write_text("invalid: yaml: content:")
        
        with pytest.raises(ExtensionInvalid, match="Invalid YAML"):
            extension_cache._validate_extension("invalid_yaml")
    
    @patch("subprocess.run")
    def test_validate_extension_invalid_compose(self, mock_run, extension_cache, sample_extension):
        """Test validation failure for invalid compose."""
        mock_run.return_value = Mock(returncode=1, stderr="Invalid compose file")
        
        with pytest.raises(ExtensionInvalid, match="Invalid compose fragment"):
            extension_cache._validate_extension("test_ext")
    
    @patch("requests.get")
    def test_add_extension_from_url(self, mock_get, extension_cache, mock_extensions_dir):
        """Test adding extension from URL."""
        # Mock successful download
        mock_response = Mock()
        mock_response.text = "version: '3.8'\nservices:\n  dev:\n    environment:\n      TEST: value"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        with patch.object(extension_cache, "_validate_extension"):
            extension_cache.add_extension("test_url_ext", "https://example.com/fragment.yml")
        
        # Check file was created
        ext_dir = mock_extensions_dir / "test_url_ext"
        assert ext_dir.exists()
        assert (ext_dir / "fragment.yml").exists()
    
    def test_add_extension_from_local_file(self, extension_cache, mock_extensions_dir, temp_dir):
        """Test adding extension from local file."""
        # Create source file
        source_file = temp_dir / "source_fragment.yml"
        source_file.write_text("version: '3.8'\nservices:\n  dev:\n    command: echo test")
        
        with patch.object(extension_cache, "_validate_extension"):
            extension_cache.add_extension("test_local_ext", str(source_file))
        
        # Check file was copied
        ext_dir = mock_extensions_dir / "test_local_ext"
        assert ext_dir.exists()
        assert (ext_dir / "docker-compose.fragment.yml").exists()
    
    def test_add_extension_from_local_directory(self, extension_cache, mock_extensions_dir, temp_dir):
        """Test adding extension from local directory."""
        # Create source directory
        source_dir = temp_dir / "source_ext"
        source_dir.mkdir()
        (source_dir / "docker-compose.fragment.yml").write_text("version: '3.8'")
        (source_dir / "Dockerfile").write_text("FROM ubuntu:22.04")
        
        with patch.object(extension_cache, "_validate_extension"):
            extension_cache.add_extension("test_dir_ext", str(source_dir))
        
        # Check directory was copied
        ext_dir = mock_extensions_dir / "test_dir_ext"
        assert ext_dir.exists()
        assert (ext_dir / "docker-compose.fragment.yml").exists()
        assert (ext_dir / "Dockerfile").exists()
    
    def test_remove_extension(self, extension_cache, sample_extension):
        """Test removing extension."""
        # Add to cache first
        hash_val = extension_cache._compute_hash(sample_extension)
        extension_cache._cache[hash_val] = "test_image:tag"
        extension_cache._save_cache()
        
        with patch("subprocess.run"):  # Mock docker rmi
            extension_cache.remove_extension("test_ext")
        
        # Check extension was removed
        assert not extension_cache.extension_exists("test_ext")
        assert not sample_extension.exists()
        assert hash_val not in extension_cache._cache
    
    def test_remove_nonexistent_extension(self, extension_cache):
        """Test removing non-existent extension."""
        with pytest.raises(ExtensionError, match="Extension nonexistent not found"):
            extension_cache.remove_extension("nonexistent")
    
    @patch("subprocess.run")
    def test_get_extension_image_cache_hit(self, mock_run, extension_cache, sample_extension):
        """Test getting extension image from cache."""
        # Pre-populate cache
        hash_val = extension_cache._compute_hash(sample_extension)
        image_tag = f"dbw_ext_test_ext:{hash_val[:12]}"
        extension_cache._cache[hash_val] = image_tag
        
        result = extension_cache.get_extension_image("test_ext")
        
        assert result == image_tag
        # Should not call docker build
        mock_run.assert_not_called()
    
    @patch("subprocess.run")
    def test_get_extension_image_cache_miss(self, mock_run, extension_cache, sample_extension):
        """Test getting extension image with cache miss."""
        mock_run.return_value = Mock(returncode=0)
        
        result = extension_cache.get_extension_image("test_ext")
        
        # Should build image
        mock_run.assert_called()
        build_call = mock_run.call_args
        assert "docker" in build_call[0][0]
        assert "buildx" in build_call[0][0]
        assert "build" in build_call[0][0]
        
        # Should return expected tag format
        hash_val = extension_cache._compute_hash(sample_extension)
        expected_tag = f"dbw_ext_test_ext:{hash_val[:12]}"
        assert result == expected_tag
    
    @patch("subprocess.run")
    def test_build_extension_image_failure(self, mock_run, extension_cache, sample_extension):
        """Test build failure handling."""
        mock_run.side_effect = subprocess.CalledProcessError(1, ["docker"], stderr="Build failed")
        
        with pytest.raises(ExtensionError, match="Failed to build extension"):
            extension_cache.get_extension_image("test_ext")


class TestDiscoverRepoExtensions:
    """Test repository extension discovery."""
    
    def test_discover_extensions(self, temp_dir):
        """Test discovering extensions in repository."""
        # Create repo extension structure
        repo_ext_dir = temp_dir / ".dbw" / "extensions"
        repo_ext_dir.mkdir(parents=True)
        
        # Create extension
        ext_dir = repo_ext_dir / "repo_ext"
        ext_dir.mkdir()
        (ext_dir / "docker-compose.fragment.yml").write_text("version: '3.8'")
        
        with patch("dbw.extension.ExtensionCache") as mock_cache_class:
            mock_cache = Mock()
            mock_cache.extension_exists.return_value = False
            mock_cache.add_extension = Mock()
            mock_cache_class.return_value = mock_cache
            
            extensions = discover_repo_extensions(temp_dir)
            
            assert extensions == ["repo_ext"]
            mock_cache.add_extension.assert_called_once_with("repo_ext", str(ext_dir))
    
    def test_discover_no_extensions(self, temp_dir):
        """Test discovery when no extensions present."""
        extensions = discover_repo_extensions(temp_dir)
        assert extensions == []


class TestParseExtensionsList:
    """Test extension list parsing."""
    
    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result = parse_extensions_list("")
        assert result == []
    
    def test_parse_single_extension(self):
        """Test parsing single extension."""
        result = parse_extensions_list("fzf")
        assert result == ["fzf"]
    
    def test_parse_multiple_extensions(self):
        """Test parsing multiple extensions."""
        result = parse_extensions_list("fzf,uv,nodejs")
        assert result == ["fzf", "uv", "nodejs"]
    
    def test_parse_with_spaces(self):
        """Test parsing with spaces."""
        result = parse_extensions_list("fzf, uv , nodejs")
        assert result == ["fzf", "uv", "nodejs"]
    
    def test_parse_with_empty_items(self):
        """Test parsing with empty items."""
        result = parse_extensions_list("fzf,,uv,")
        assert result == ["fzf", "uv"]


class TestValidateExtensions:
    """Test extension validation."""
    
    def test_validate_existing_extensions(self):
        """Test validation of existing extensions."""
        with patch("dbw.extension.ExtensionCache") as mock_cache_class:
            mock_cache = Mock()
            mock_cache.extension_exists.return_value = True
            mock_cache_class.return_value = mock_cache
            
            # Should not raise
            validate_extensions(["ext1", "ext2"])
    
    def test_validate_missing_extensions(self):
        """Test validation with missing extensions."""
        with patch("dbw.extension.ExtensionCache") as mock_cache_class:
            mock_cache = Mock()
            mock_cache.extension_exists.side_effect = lambda name: name == "existing"
            mock_cache.list_extensions.return_value = ["existing", "other"]
            mock_cache_class.return_value = mock_cache
            
            with pytest.raises(ExtensionError, match="Extensions not found: \\['missing'\\]"):
                validate_extensions(["existing", "missing"])
    
    def test_validate_empty_list(self):
        """Test validation of empty extension list."""
        # Should not raise
        validate_extensions([])