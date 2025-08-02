"""Basic tests for DBW functionality."""

from dbw import __version__, main, DbwError


def test_version():
    """Test that version is properly set."""
    assert __version__ == "0.2.0"


def test_main_import():
    """Test that main CLI function can be imported."""
    assert callable(main)


def test_dbw_error_import():
    """Test that DbwError can be imported."""
    assert issubclass(DbwError, Exception)
