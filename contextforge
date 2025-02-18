#!/usr/bin/env python3
"""ContextForge - Modern Code Processing and Filtering Tool"""

import os
import re
import sys
import subprocess
import tempfile
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional, List, Pattern
from datetime import datetime

# Ensure dependencies are installed
REQUIRED_PACKAGES = ['click', 'rich', 'pygithub', 'gitpython', 'pathspec']

def ensure_dependencies():
    try:
        for package in REQUIRED_PACKAGES:
            __import__(package)
    except ImportError:
        print("Installing required dependencies...")
        try:
            # Try using uv first
            subprocess.check_call(["uv", "pip", "install"] + REQUIRED_PACKAGES)
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fall back to pip if uv is not available
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + REQUIRED_PACKAGES)
        print("Dependencies installed successfully!")

ensure_dependencies()

import click
from github import Github
from git import Repo
from rich.console import Console
from rich.theme import Theme

# Create a custom theme for consistent styling
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "success": "green bold",
    "path": "blue",
})

console = Console(theme=custom_theme)
global_index = 1

# Constants
GITHUB_URL_PATTERN = r"https?://github\.com/([^/]+)/([^/]+)"
TEMP_DIR_PREFIX = "contextforge_"


def should_ignore(path, gitignore_rules):
    for rule in gitignore_rules:
        if fnmatch(os.path.basename(path), rule):
            return True
        if os.path.isdir(path) and fnmatch(os.path.basename(path) + "/", rule):
            return True
    return False


def read_gitignore(path):
    gitignore_path = os.path.join(path, ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r") as f:
            return [
                line.strip() for line in f if line.strip() and not line.startswith("#")
            ]
    return []


def add_line_numbers(content):
    lines = content.splitlines()

    padding = len(str(len(lines)))

    numbered_lines = [f"{i+1:{padding}}  {line}" for i, line in enumerate(lines)]
    return "\n".join(numbered_lines)


def print_path(writer, path, content, xml, line_numbers):
    if xml:
        print_as_xml(writer, path, content, line_numbers)
    else:
        print_default(writer, path, content, line_numbers)


def print_default(writer, path, content, line_numbers):
    writer(path)
    writer("---")
    if line_numbers:
        content = add_line_numbers(content)
    writer(content)
    writer("")
    writer("---")


def print_as_xml(writer, path, content, line_numbers):
    global global_index
    writer(f'<document index="{global_index}">')
    writer(f"<source>{path}</source>")
    writer("<document_content>")
    if line_numbers:
        content = add_line_numbers(content)
    writer(content)
    writer("</document_content>")
    writer("</document>")
    global_index += 1


def should_include_file(
    file_path: str,
    extensions: tuple,
    regex_pattern: Optional[str],
    min_size: Optional[int],
    max_size: Optional[int],
    modified_after: Optional[click.DateTime],
) -> bool:
    """Check if a file should be included based on all filtering criteria."""
    # Check file extension
    if extensions and not any(file_path.endswith(ext) for ext in extensions):
        return False

    # Check regex pattern
    if regex_pattern and not re.search(regex_pattern, file_path):
        return False

    # Get file stats
    try:
        stats = os.stat(file_path)
    except OSError:
        return False

    # Check file size
    if min_size is not None and stats.st_size < min_size:
        return False
    if max_size is not None and stats.st_size > max_size:
        return False

    # Check modification time
    if modified_after is not None:
        mod_time = datetime.fromtimestamp(stats.st_mtime)
        if mod_time < modified_after:
            return False

    return True


def process_path(
    path,
    extensions,
    include_hidden,
    ignore_files_only,
    ignore_gitignore,
    gitignore_rules,
    ignore_patterns,
    writer,
    claude_xml,
    line_numbers=False,
    regex_pattern=None,
    min_size=None,
    max_size=None,
    modified_after=None,
):
    """Process a path with enhanced filtering capabilities."""
    if os.path.isfile(path):
        if should_include_file(path, extensions, regex_pattern, min_size, max_size, modified_after):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    print_path(writer, path, f.read(), claude_xml, line_numbers)
            except UnicodeDecodeError:
                console.print(f"[warning]⚠️  Skipping binary file: {path}[/]")
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            if not include_hidden:
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                files = [f for f in files if not f.startswith(".")]

            if not ignore_gitignore:
                gitignore_rules.extend(read_gitignore(root))
                dirs[:] = [
                    d
                    for d in dirs
                    if not should_ignore(os.path.join(root, d), gitignore_rules)
                ]
                files = [
                    f
                    for f in files
                    if not should_ignore(os.path.join(root, f), gitignore_rules)
                ]

            if ignore_patterns:
                if not ignore_files_only:
                    dirs[:] = [
                        d
                        for d in dirs
                        if not any(fnmatch(d, pattern) for pattern in ignore_patterns)
                    ]
                files = [
                    f
                    for f in files
                    if not any(fnmatch(f, pattern) for pattern in ignore_patterns)
                ]

            for file in sorted(files):
                file_path = os.path.join(root, file)
                if should_include_file(file_path, extensions, regex_pattern, min_size, max_size, modified_after):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            print_path(
                                writer, file_path, f.read(), claude_xml, line_numbers
                            )
                    except UnicodeDecodeError:
                        console.print(f"[warning]⚠️  Skipping binary file: {file_path}[/]")


def is_github_url(url: str) -> bool:
    """Check if the given URL is a valid GitHub repository URL."""
    return bool(re.match(GITHUB_URL_PATTERN, url))


def clone_github_repo(url: str) -> str:
    """Clone a GitHub repository to a temporary directory and return the path."""
    with tempfile.TemporaryDirectory(prefix=TEMP_DIR_PREFIX) as temp_dir:
        try:
            console.print(f"[info]📦 Cloning repository: {url}[/]")
            Repo.clone_from(url, temp_dir)
            console.print(f"[success]✓ Repository cloned successfully[/]")
            return temp_dir
        except Exception as e:
            console.print(f"[error]❌ Error cloning repository: {e}[/]")
            raise click.BadArgumentUsage(f"Failed to clone repository: {e}")


def process_github_url(
    url: str,
    extensions: tuple,
    include_hidden: bool,
    ignore_files_only: bool,
    ignore_gitignore: bool,
    ignore_patterns: tuple,
    writer,
    claude_xml: bool,
    line_numbers: bool,
) -> None:
    """Process a GitHub repository URL."""
    temp_dir = clone_github_repo(url)
    gitignore_rules = [] if ignore_gitignore else read_gitignore(temp_dir)
    
    if claude_xml:
        writer("<documents>")
    
    process_path(
        temp_dir,
        extensions,
        include_hidden,
        ignore_files_only,
        ignore_gitignore,
        gitignore_rules,
        ignore_patterns,
        writer,
        claude_xml,
        line_numbers,
    )
    
    if claude_xml:
        writer("</documents>")


@click.command()
@click.argument("paths", nargs=-1, type=str)
@click.option("extensions", "-e", "--extension", multiple=True, help="Filter by file extensions (e.g., -e py -e md)")
@click.option(
    "--include-hidden",
    is_flag=True,
    help="Include files and folders starting with .",
)
@click.option(
    "--ignore-files-only",
    is_flag=True,
    help="--ignore option only ignores files",
)
@click.option(
    "--ignore-gitignore",
    is_flag=True,
    help="Ignore .gitignore files and include all files",
)
@click.option(
    "ignore_patterns",
    "--ignore",
    multiple=True,
    default=[],
    help="List of patterns to ignore",
)
@click.option(
    "regex_pattern",
    "--regex",
    help="Filter files using a regular expression pattern",
)
@click.option(
    "min_size",
    "--min-size",
    type=click.INT,
    help="Filter files larger than size (in bytes)",
)
@click.option(
    "max_size",
    "--max-size",
    type=click.INT,
    help="Filter files smaller than size (in bytes)",
)
@click.option(
    "modified_after",
    "--modified-after",
    type=click.DateTime(),
    help="Filter files modified after date (YYYY-MM-DD)",
)
@click.option(
    "output_file",
    "-o",
    "--output",
    type=click.Path(writable=True),
    help="Output to a file instead of stdout",
)
@click.option(
    "claude_xml",
    "-c",
    "--cxml",
    is_flag=True,
    help="Output in Claude-optimized XML format",
)
@click.option(
    "line_numbers",
    "-n",
    "--line-numbers",
    is_flag=True,
    help="Add line numbers to the output",
)
@click.version_option()
def cli(
    paths,
    extensions,
    include_hidden,
    ignore_files_only,
    ignore_gitignore,
    ignore_patterns,
    regex_pattern,
    min_size,
    max_size,
    modified_after,
    output_file,
    claude_xml,
    line_numbers,
):
    """🔍 ContextForge: Modern Code Processing and Filtering Tool

    A powerful tool for processing and filtering code from local directories and GitHub repositories.
    Perfect for AI model training, code analysis, and documentation generation.

    \b
    🚀 Basic Usage:
    ────────────────────────────────────────────────────
      # Process a local directory
      $ contextforge .
      
      # Process a GitHub repository
      $ contextforge https://github.com/user/repo
      
      # Filter by file extensions
      $ contextforge . -e py -e md

    \b
    🔧 Advanced Filtering:
    ────────────────────────────────────────────────────
      # Find Python test files modified in the last week
      $ contextforge . -e py --regex "test_.*\\.py$" \\
          --modified-after 2024-03-10
      
      # Get all JavaScript files between 1KB and 1MB
      $ contextforge . -e js --min-size 1024 --max-size 1048576
      
      # Process specific files in a GitHub repo
      $ contextforge https://github.com/user/repo \\
          -e py --regex "src/.*controller\\.py$"

    \b
    📝 Output Options:
    ────────────────────────────────────────────────────
      # Generate Claude-optimized XML with line numbers
      $ contextforge . --cxml -n -o output.xml
      
      # Process multiple paths with custom ignore patterns
      $ contextforge src tests \\
          --ignore "*.pyc" \\
          --ignore "*/__pycache__/*" \\
          --ignore-files-only

    \b
    💡 Common Use Cases:
    ────────────────────────────────────────────────────
      # Prepare AI training data
      $ contextforge . -e py -e js -e ts --cxml -o training.xml
      
      # Code review of recent changes
      $ contextforge . --modified-after 2024-03-01 \\
          --regex ".*\\.(py|js)$" -n
      
      # Documentation generation
      $ contextforge . --regex ".*\\.md$" \\
          --ignore "node_modules/*" -o docs.txt
      
      # Repository analysis
      $ contextforge https://github.com/user/repo \\
          --regex ".*\\.(py|js)$" \\
          --min-size 1000 \\
          --ignore "tests/*" \\
          -n -o analysis.txt

    \b
    📚 Learn More:
    ────────────────────────────────────────────────────
    Documentation: https://github.com/yourusername/contextforge
    """
    console.print("[success]🔍 ContextForge[/] - Processing files...\n")

    # Setup writer
    writer = click.echo
    fp = None
    if output_file:
        fp = open(output_file, "w", encoding="utf-8")
        def writer(s):
            return print(s, file=fp)

    try:
        # Process each path
        for path in paths:
            if is_github_url(path):
                process_github_url(
                    path,
                    extensions,
                    include_hidden,
                    ignore_files_only,
                    ignore_gitignore,
                    ignore_patterns,
                    writer,
                    claude_xml,
                    line_numbers,
                )
            else:
                if not os.path.exists(path):
                    raise click.BadArgumentUsage(f"Path does not exist: {path}")
                
                gitignore_rules = [] if ignore_gitignore else read_gitignore(os.path.dirname(path))
                
                if claude_xml and path == paths[0]:
                    writer("<documents>")
                
                process_path(
                    path,
                    extensions,
                    include_hidden,
                    ignore_files_only,
                    ignore_gitignore,
                    gitignore_rules,
                    ignore_patterns,
                    writer,
                    claude_xml,
                    line_numbers,
                    regex_pattern,
                    min_size,
                    max_size,
                    modified_after,
                )
                
                if claude_xml and path == paths[-1]:
                    writer("</documents>")
    
    finally:
        if fp:
            fp.close()
        console.print("\n[success]✨ Processing complete![/]")

if __name__ == "__main__":
    cli()
