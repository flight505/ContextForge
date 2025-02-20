import os
from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from contextforge import cli, is_github_url


def test_basic_functionality(tmpdir):
    """Test basic file reading functionality."""
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "file1.txt" in result.output
        assert "Contents of file1" in result.output


def test_include_hidden(tmpdir):
    """Test hidden file handling."""
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/.hidden.txt", "w") as f:
            f.write("Hidden file")

        # Should not include hidden by default
        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert ".hidden.txt" not in result.output

        # Should include with flag
        result = runner.invoke(cli, ["test_dir", "--include-hidden"])
        assert result.exit_code == 0
        assert ".hidden.txt" in result.output


def test_ignore_patterns(tmpdir):
    """Test ignore pattern functionality."""
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/ignore.txt", "w") as f:
            f.write("Ignore this")
        with open("test_dir/keep.py", "w") as f:
            f.write("Keep this")

        result = runner.invoke(cli, ["test_dir", "--ignore", "*.txt"])
        assert result.exit_code == 0
        assert "ignore.txt" not in result.output
        assert "keep.py" in result.output


def test_extension_filter(tmpdir):
    """Test file extension filtering."""
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/test.py", "w") as f:
            f.write("Python file")
        with open("test_dir/test.txt", "w") as f:
            f.write("Text file")

        result = runner.invoke(cli, ["test_dir", "-e", "py"])
        assert result.exit_code == 0
        assert "test.py" in result.output
        assert "test.txt" not in result.output


def test_output_file(tmpdir):
    """Test output to file functionality."""
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/test.txt", "w") as f:
            f.write("Test content")

        output_file = "output.txt"
        result = runner.invoke(cli, ["test_dir", "-o", output_file])
        assert result.exit_code == 0
        
        with open(output_file, "r") as f:
            content = f.read()
            assert "test.txt" in content
            assert "Test content" in content


def test_github_url_detection():
    """Test GitHub URL detection."""
    assert is_github_url("https://github.com/user/repo") is True
    assert is_github_url("https://example.com/user/repo") is False


@patch('contextforge.Repo')
def test_github_repo_cloning(mock_repo):
    """Test GitHub repository cloning."""
    runner = CliRunner()
    mock_repo.clone_from = MagicMock()
    
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["https://github.com/user/repo"])
        assert result.exit_code == 0
        mock_repo.clone_from.assert_called_once()


def test_error_handling(tmpdir):
    """Test basic error handling."""
    runner = CliRunner()
    result = runner.invoke(cli, ["non_existent_path"])
    assert result.exit_code == 1
    assert "Error" in result.output or "error" in result.output