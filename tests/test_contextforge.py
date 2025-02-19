import os
import pytest
from datetime import datetime, timedelta
from unittest import mock
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from contextforge import cli, clone_github_repo, is_github_url


def test_basic_functionality(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "test_dir/file1.txt" in result.output
        assert "Contents of file1" in result.output
        assert "test_dir/file2.txt" in result.output
        assert "Contents of file2" in result.output


def test_include_hidden(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/.hidden.txt", "w") as f:
            f.write("Contents of hidden file")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "test_dir/.hidden.txt" not in result.output

        result = runner.invoke(cli, ["test_dir", "--include-hidden"])
        assert result.exit_code == 0
        assert "test_dir/.hidden.txt" in result.output
        assert "Contents of hidden file" in result.output


def test_ignore_gitignore(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/.gitignore", "w") as f:
            f.write("ignored.txt")
        with open("test_dir/ignored.txt", "w") as f:
            f.write("This file should be ignored")
        with open("test_dir/included.txt", "w") as f:
            f.write("This file should be included")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "test_dir/ignored.txt" not in result.output
        assert "test_dir/included.txt" in result.output

        result = runner.invoke(cli, ["test_dir", "--ignore-gitignore"])
        assert result.exit_code == 0
        assert "test_dir/ignored.txt" in result.output
        assert "This file should be ignored" in result.output
        assert "test_dir/included.txt" in result.output


def test_multiple_paths(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir1")
        with open("test_dir1/file1.txt", "w") as f:
            f.write("Contents of file1")
        os.makedirs("test_dir2")
        with open("test_dir2/file2.txt", "w") as f:
            f.write("Contents of file2")
        with open("single_file.txt", "w") as f:
            f.write("Contents of single file")

        result = runner.invoke(cli, ["test_dir1", "test_dir2", "single_file.txt"])
        assert result.exit_code == 0
        assert "test_dir1/file1.txt" in result.output
        assert "Contents of file1" in result.output
        assert "test_dir2/file2.txt" in result.output
        assert "Contents of file2" in result.output
        assert "single_file.txt" in result.output
        assert "Contents of single file" in result.output


def test_ignore_patterns(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir", exist_ok=True)
        with open("test_dir/file_to_ignore.txt", "w") as f:
            f.write("This file should be ignored due to ignore patterns")
        with open("test_dir/file_to_include.txt", "w") as f:
            f.write("This file should be included")

        result = runner.invoke(cli, ["test_dir", "--ignore", "*.txt"])
        assert result.exit_code == 0
        assert "test_dir/file_to_ignore.txt" not in result.output
        assert "This file should be ignored due to ignore patterns" not in result.output
        assert "test_dir/file_to_include.txt" not in result.output

        os.makedirs("test_dir/test_subdir", exist_ok=True)
        with open("test_dir/test_subdir/any_file.txt", "w") as f:
            f.write("This entire subdirectory should be ignored due to ignore patterns")
        result = runner.invoke(cli, ["test_dir", "--ignore", "*subdir*"])
        assert result.exit_code == 0
        assert "test_dir/test_subdir/any_file.txt" not in result.output
        assert (
            "This entire subdirectory should be ignored due to ignore patterns"
            not in result.output
        )
        assert "test_dir/file_to_include.txt" in result.output
        assert "This file should be included" in result.output
        assert "This file should be included" in result.output

        result = runner.invoke(cli, ["test_dir", "--ignore", "*subdir*", "--ignore-files-only"])
        assert result.exit_code == 0
        assert "test_dir/test_subdir/any_file.txt" in result.output

        result = runner.invoke(cli, ["test_dir", "--ignore", ""])


def test_specific_extensions(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        # Write one.txt one.py two/two.txt two/two.py three.md
        os.makedirs("test_dir/two")
        with open("test_dir/one.txt", "w") as f:
            f.write("This is one.txt")
        with open("test_dir/one.py", "w") as f:
            f.write("This is one.py")
        with open("test_dir/two/two.txt", "w") as f:
            f.write("This is two/two.txt")
        with open("test_dir/two/two.py", "w") as f:
            f.write("This is two/two.py")
        with open("test_dir/three.md", "w") as f:
            f.write("This is three.md")

        # Try with -e py -e md
        result = runner.invoke(cli, ["test_dir", "-e", "py", "-e", "md"])
        assert result.exit_code == 0
        assert ".txt" not in result.output
        assert "test_dir/one.py" in result.output
        assert "test_dir/two/two.py" in result.output
        assert "test_dir/three.md" in result.output


def test_mixed_paths_with_options(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/.gitignore", "w") as f:
            f.write("ignored_in_gitignore.txt\n.hidden_ignored_in_gitignore.txt")
        with open("test_dir/ignored_in_gitignore.txt", "w") as f:
            f.write("This file should be ignored by .gitignore")
        with open("test_dir/.hidden_ignored_in_gitignore.txt", "w") as f:
            f.write("This hidden file should be ignored by .gitignore")
        with open("test_dir/included.txt", "w") as f:
            f.write("This file should be included")
        with open("test_dir/.hidden_included.txt", "w") as f:
            f.write("This hidden file should be included")
        with open("single_file.txt", "w") as f:
            f.write("Contents of single file")

        result = runner.invoke(cli, ["test_dir", "single_file.txt"])
        assert result.exit_code == 0
        assert "test_dir/ignored_in_gitignore.txt" not in result.output
        assert "test_dir/.hidden_ignored_in_gitignore.txt" not in result.output
        assert "test_dir/included.txt" in result.output
        assert "test_dir/.hidden_included.txt" not in result.output
        assert "single_file.txt" in result.output
        assert "Contents of single file" in result.output

        result = runner.invoke(cli, ["test_dir", "single_file.txt", "--include-hidden"])
        assert result.exit_code == 0
        assert "test_dir/ignored_in_gitignore.txt" not in result.output
        assert "test_dir/.hidden_ignored_in_gitignore.txt" not in result.output
        assert "test_dir/included.txt" in result.output
        assert "test_dir/.hidden_included.txt" in result.output
        assert "single_file.txt" in result.output
        assert "Contents of single file" in result.output

        result = runner.invoke(
            cli, ["test_dir", "single_file.txt", "--ignore-gitignore"]
        )
        assert result.exit_code == 0
        assert "test_dir/ignored_in_gitignore.txt" in result.output
        assert "test_dir/.hidden_ignored_in_gitignore.txt" not in result.output
        assert "test_dir/included.txt" in result.output
        assert "test_dir/.hidden_included.txt" not in result.output
        assert "single_file.txt" in result.output
        assert "Contents of single file" in result.output

        result = runner.invoke(
            cli,
            ["test_dir", "single_file.txt", "--ignore-gitignore", "--include-hidden"],
        )
        assert result.exit_code == 0
        assert "test_dir/ignored_in_gitignore.txt" in result.output
        assert "test_dir/.hidden_ignored_in_gitignore.txt" in result.output
        assert "test_dir/included.txt" in result.output
        assert "test_dir/.hidden_included.txt" in result.output
        assert "single_file.txt" in result.output
        assert "Contents of single file" in result.output


def test_binary_file_warning(tmpdir):
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/binary_file.bin", "wb") as f:
            f.write(b"\xff")
        with open("test_dir/text_file.txt", "w") as f:
            f.write("This is a text file")

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0

        stdout = result.stdout
        stderr = result.stderr

        assert "test_dir/text_file.txt" in stdout
        assert "This is a text file" in stdout
        assert "\ntest_dir/binary_file.bin" not in stdout
        assert (
            "Warning: Skipping file test_dir/binary_file.bin due to UnicodeDecodeError"
            in stderr
        )


@pytest.mark.parametrize(
    "args", (["test_dir"], ["test_dir/file1.txt", "test_dir/file2.txt"])
)
def test_xml_format_dir(tmpdir, args):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1.txt")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2.txt")
        result = runner.invoke(cli, args + ["--cxml"])
        assert result.exit_code == 0
        actual = result.output
        expected = """
<documents>
<document index="1">
<source>test_dir/file1.txt</source>
<document_content>
Contents of file1.txt
</document_content>
</document>
<document index="2">
<source>test_dir/file2.txt</source>
<document_content>
Contents of file2.txt
</document_content>
</document>
</documents>
"""
        assert expected.strip() == actual.strip()


@pytest.mark.parametrize("arg", ("-o", "--output"))
def test_output_option(tmpdir, arg):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        with open("test_dir/file1.txt", "w") as f:
            f.write("Contents of file1.txt")
        with open("test_dir/file2.txt", "w") as f:
            f.write("Contents of file2.txt")
        output_file = "output.txt"
        result = runner.invoke(
            cli, ["test_dir", arg, output_file], catch_exceptions=False
        )
        assert result.exit_code == 0
        assert not result.output
        with open(output_file, "r") as f:
            actual = f.read()
            
        # Normalize newlines and whitespace for comparison
        def normalize(text):
            # Split by double newlines to preserve empty lines between entries
            entries = text.strip().split("\n\n")
            # Normalize each entry
            normalized_entries = [
                "\n".join(line.strip() for line in entry.split("\n"))
                for entry in entries
            ]
            # Join entries with double newlines
            return "\n\n".join(normalized_entries)
            
        expected = """test_dir/file1.txt
---
Contents of file1.txt

---

test_dir/file2.txt
---
Contents of file2.txt

---"""
        # Print actual and expected for debugging
        print("\nActual output:")
        print(repr(actual))
        print("\nExpected output:")
        print(repr(expected))
        assert actual.strip() == expected.strip()


def test_line_numbers(tmpdir):
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        test_content = "First line\nSecond line\nThird line\nFourth line\n"
        with open("test_dir/multiline.txt", "w") as f:
            f.write(test_content)

        result = runner.invoke(cli, ["test_dir"])
        assert result.exit_code == 0
        assert "1  First line" not in result.output
        assert test_content in result.output

        result = runner.invoke(cli, ["test_dir", "-n"])
        assert result.exit_code == 0
        assert "1  First line" in result.output
        assert "2  Second line" in result.output
        assert "3  Third line" in result.output
        assert "4  Fourth line" in result.output

        result = runner.invoke(cli, ["test_dir", "--line-numbers"])
        assert result.exit_code == 0
        assert "1  First line" in result.output
        assert "2  Second line" in result.output
        assert "3  Third line" in result.output
        assert "4  Fourth line" in result.output


def test_github_url_detection():
    """Test GitHub URL detection functionality."""
    valid_urls = [
        "https://github.com/user/repo",
        "http://github.com/user/repo",
        "https://github.com/organization/project-name",
    ]
    invalid_urls = [
        "https://gitlab.com/user/repo",
        "https://github.com/only-user",
        "https://example.com/user/repo",
    ]
    
    for url in valid_urls:
        assert is_github_url(url) is True
        
    for url in invalid_urls:
        assert is_github_url(url) is False


@patch('contextforge.Repo')
def test_github_repo_cloning(mock_repo):
    """Test GitHub repository cloning functionality."""
    runner = CliRunner()
    mock_repo.clone_from = MagicMock()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["https://github.com/user/repo"])
        assert result.exit_code == 0
        mock_repo.clone_from.assert_called_once_with(
            "https://github.com/user/repo",
            mock.ANY
        )


def test_enhanced_filtering(tmpdir):
    """Test enhanced filtering capabilities."""
    runner = CliRunner()
    with tmpdir.as_cwd():
        # Create test files with different sizes and dates
        os.makedirs("test_dir")
        
        # Create files with different sizes
        with open("test_dir/small.txt", "w") as f:
            f.write("small")  # 5 bytes
        with open("test_dir/medium.txt", "w") as f:
            f.write("medium" * 100)  # 600 bytes
        with open("test_dir/large.txt", "w") as f:
            f.write("large" * 1000)  # 5000 bytes
            
        # Test size filtering
        result = runner.invoke(cli, ["test_dir", "--min-size", "500"])
        assert result.exit_code == 0
        assert "small.txt" not in result.output
        assert "medium.txt" in result.output
        assert "large.txt" in result.output
        
        result = runner.invoke(cli, ["test_dir", "--max-size", "1000"])
        assert result.exit_code == 0
        assert "small.txt" in result.output
        assert "medium.txt" in result.output
        assert "large.txt" not in result.output
        
        # Test regex filtering
        result = runner.invoke(cli, ["test_dir", "--regex", "medium.*"])
        assert result.exit_code == 0
        assert "small.txt" not in result.output
        assert "medium.txt" in result.output
        assert "large.txt" not in result.output


def test_modification_time_filtering(tmpdir):
    """Test file modification time filtering."""
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        
        # Create files with different modification times
        with open("test_dir/old.txt", "w") as f:
            f.write("old file")
        with open("test_dir/new.txt", "w") as f:
            f.write("new file")
            
        # Set old file's modification time to 2 days ago
        old_time = datetime.now() - timedelta(days=2)
        os.utime("test_dir/old.txt", (old_time.timestamp(), old_time.timestamp()))
        
        # Test modification time filtering
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        result = runner.invoke(cli, ["test_dir", "--modified-after", yesterday])
        assert result.exit_code == 0
        assert "old.txt" not in result.output
        assert "new.txt" in result.output


def test_combined_filtering(tmpdir):
    """Test multiple filtering criteria combined."""
    runner = CliRunner()
    with tmpdir.as_cwd():
        os.makedirs("test_dir")
        
        # Create test files
        files = {
            "test_small.py": "small py",  # 8 bytes
            "test_medium.py": "medium" * 100,  # 600 bytes
            "prod_large.py": "large" * 1000,  # 5000 bytes
            "test_other.txt": "other",  # 5 bytes
        }
        
        for name, content in files.items():
            with open(f"test_dir/{name}", "w") as f:
                f.write(content)
        
        # Test combined filtering (extension + regex + size)
        result = runner.invoke(cli, [
            "test_dir",
            "-e", "py",
            "--regex", "test_.*",
            "--min-size", "100",
            "--max-size", "1000"
        ])
        
        assert result.exit_code == 0
        assert "test_small.py" not in result.output  # too small
        assert "test_medium.py" in result.output  # matches all criteria
        assert "prod_large.py" not in result.output  # doesn't match regex
        assert "test_other.txt" not in result.output  # wrong extension


def test_error_handling(tmpdir):
    """Test error handling for various scenarios."""
    runner = CliRunner(mix_stderr=False)
    with tmpdir.as_cwd():
        # Test invalid regex pattern
        result = runner.invoke(cli, [".", "--regex", "[invalid"])
        assert result.exit_code == 1
        assert "Invalid regex pattern: [invalid" in result.stderr

        # Test non-existent path
        result = runner.invoke(cli, ["non_existent_path"])
        assert result.exit_code == 1
        assert "Error processing non_existent_path" in result.stderr