#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "click",
#   "rich",
#   "pygithub",
#   "gitpython",
#   "pathspec"
# ]
# ///

import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from fnmatch import fnmatch
from typing import Callable, List, Optional

import click
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
err_console = Console(theme=custom_theme, file=click.get_text_stream('stderr'))

# Global document index used in XML output.
document_index = 1

# Constants
GITHUB_URL_PATTERN = r"https?://github\.com/([^/]+)/([^/]+)"
TEMP_DIR_PREFIX = "contextforge_"

# Common binary file extensions and magic numbers
BINARY_EXTENSIONS = {
    # Executables and Libraries
    '.exe', '.dll', '.so', '.dylib', '.bin', '.pyc', '.pyo',
    # Images
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp',
    # Documents
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    # Archives
    '.zip', '.tar', '.gz', '.7z', '.rar',
    # Other
    '.class', '.jar', '.war', '.ear'
}

# Magic numbers (file signatures) for common binary formats
MAGIC_NUMBERS = {
    b'\x89PNG\r\n\x1a\n': '.png',
    b'\xff\xd8\xff': '.jpg',
    b'GIF8': '.gif',
    b'PK\x03\x04': '.zip',
    b'%PDF': '.pdf',
}

def should_ignore(path: str, ignore_rules: List[str]) -> bool:
    basename = os.path.basename(path)
    for rule in ignore_rules:
        if fnmatch(basename, rule):
            return True
        if os.path.isdir(path) and fnmatch(basename + "/", rule):
            return True
    return False

def read_gitignore(directory: str) -> List[str]:
    gitignore_path = os.path.join(directory, ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, "r") as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    return []

def add_line_numbers(content: str) -> str:
    lines = content.splitlines()
    padding = len(str(len(lines)))
    numbered_lines = [f"{i+1:{padding}}  {line}" for i, line in enumerate(lines)]
    return "\n".join(numbered_lines)

def print_repo_tree(writer: Callable[[str], None], base_path: str, max_depth: int = 1):
    """
    Print a simplified repository tree (up to a certain depth).
    Skips large subdirectories or deeply nested structures.
    """
    writer("\n[DATASET-MODE] Repository Tree Overview\n")
    writer("----------------------------------------\n")

    def walk_dir(current_path: str, depth: int = 0):
        if depth > max_depth:
            return
        try:
            entries = sorted(os.listdir(current_path))
        except PermissionError:
            return
        dirs = []
        files = []
        for entry in entries:
            full_entry = os.path.join(current_path, entry)
            if os.path.isdir(full_entry):
                dirs.append(entry)
            else:
                files.append(entry)
        # Print dirs
        for d in dirs:
            rel_dir = os.path.relpath(os.path.join(current_path, d), base_path)
            indent = "  " * depth
            writer(f"{indent}📂 {rel_dir}/\n")
            # If there's a huge subdir, let's not expand it (simple heuristic)
            sub_entries = os.listdir(os.path.join(current_path, d))
            if len(sub_entries) < 50:  # you can tweak this threshold
                walk_dir(os.path.join(current_path, d), depth + 1)
            else:
                writer(f"{indent}  (... {len(sub_entries)} items omitted ...)\n")
        # Print files
        for f in files:
            rel_file = os.path.relpath(os.path.join(current_path, f), base_path)
            indent = "  " * depth
            writer(f"{indent}📄 {rel_file}\n")

    # Start from base_path
    walk_dir(base_path, depth=0)
    writer("\n")

def print_file_summary(writer: Callable[[str], None], file_path: str):
    """Print a lightweight file summary line."""
    try:
        size_bytes = os.path.getsize(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        line_count = len(lines)
        # Attempt to get a snippet from the first non-empty line
        snippet = ""
        for line in lines:
            line_stripped = line.strip()
            if line_stripped:
                snippet = line_stripped[:60]  # 60 chars limit
                break
        summary = (
            f"[SUMMARY] {file_path} | {size_bytes} bytes | {line_count} lines"
            f"{f' | snippet: {snippet}' if snippet else ''}"
        )
        writer(f"{summary}\n")
    except Exception:  # Remove the unused variable e
        # fallback if any error reading file
        writer(f"[SUMMARY] {file_path} (unavailable)\n")

def print_default(
    writer: Callable[[str], None],
    path: str,
    content: str,
    line_numbers: bool,
    dataset_mode: bool,
) -> None:
    """Print file content in plain text format, with optional dataset-mode delimiter."""
    if dataset_mode:
        # Unique delimiter for dataset mode
        writer(f"\n===== FILE BEGIN: {path} =====\n")
    else:
        writer(f"{path}\n")
        writer("---\n")

    writer(add_line_numbers(content) if line_numbers else content)

    if dataset_mode:
        writer(f"\n===== FILE END: {path} =====\n\n")
    else:
        # Add newlines and marker for separation
        writer("\n\n---\n\n")

def print_as_xml(
    writer: Callable[[str], None], 
    path: str, 
    content: str, 
    line_numbers: bool
) -> None:
    global document_index
    writer(f"<document index=\"{document_index}\">\n")
    writer(f"<source>{path}</source>\n")
    writer("<document_content>\n")
    writer(add_line_numbers(content) if line_numbers else content)
    writer("\n</document_content>\n")
    writer("</document>\n")
    document_index += 1

def print_as_json(
    writer: Callable[[str], None], 
    path: str, 
    content: str, 
    line_numbers: bool
) -> None:
    """Print content in JSON format."""
    data = {
        "path": path,
        "content": add_line_numbers(content) if line_numbers else content
    }
    writer(json.dumps(data))  # No newline for JSON array format

def print_as_jsonl(
    writer: Callable[[str], None], 
    path: str, 
    content: str, 
    line_numbers: bool
) -> None:
    """Print content in JSONL format (one JSON object per line)."""
    data = {
        "path": path,
        "content": add_line_numbers(content) if line_numbers else content
    }
    writer(json.dumps(data) + "\n")

def print_path(writer: Callable[[str], None], path: str, content: str,
               use_xml: bool, use_json: bool, use_jsonl: bool,
               line_numbers: bool, dataset_mode: bool) -> None:
    """
    Print the file content using the selected output format,
    optionally including dataset-mode extras.
    """
    if use_xml:
        print_as_xml(writer, path, content, line_numbers)
    elif use_json:
        print_as_json(writer, path, content, line_numbers)
    elif use_jsonl:
        print_as_jsonl(writer, path, content, line_numbers)
    else:
        print_default(writer, path, content, line_numbers, dataset_mode)

def should_include_file(
    file_path: str,
    extensions: tuple,
    regex_pattern: Optional[str],
    min_size: Optional[int],
    max_size: Optional[int],
    modified_after: Optional[datetime],
) -> bool:
    if extensions and not any(file_path.endswith(ext) for ext in extensions):
        return False
    if regex_pattern and not re.search(regex_pattern, file_path):
        return False
    try:
        stats = os.stat(file_path)
    except OSError:
        return False
    if min_size is not None and stats.st_size < min_size:
        return False
    if max_size is not None and stats.st_size > max_size:
        return False
    if modified_after is not None:
        mod_time = datetime.fromtimestamp(stats.st_mtime)
        if mod_time < modified_after:
            return False
    return True

def is_binary_content(content: bytes, sample_size: int = 1024) -> bool:
    """Check if content appears to be binary using a heuristic."""
    if b'\x00' in content[:sample_size]:
        return True

    text_characters = (
        b''.join(map(bytes, [range(32, 127)]))
        + b''.join(map(bytes, [range(128, 256)]))
        + b'\n\r\t\f\b'
    )
    non_text = sum(byte not in text_characters for byte in content[:sample_size])
    return non_text / len(content[:sample_size]) > 0.30

def is_binary_file(file_path: str) -> bool:
    """Determine if a file is binary using multiple methods."""
    # 1. Check extension first (fast path)
    if any(file_path.lower().endswith(ext) for ext in BINARY_EXTENSIONS):
        return True

    try:
        # 2. Read first 8KB for magic numbers and content analysis
        with open(file_path, 'rb') as f:
            header = f.read(8192)
            if not header:
                return False
            # Check magic numbers
            for magic, _ in MAGIC_NUMBERS.items():
                if header.startswith(magic):
                    return True
            return is_binary_content(header)
    except (OSError, IOError) as e:
        err_console.print(
            f"[warning]Warning: Error reading {file_path}: "
            f"{str(e)}[/warning]"
        )
        return True  # Treat as binary on error

    return False

def process_local_path(
    path: str,
    extensions: tuple,
    include_hidden: bool,
    ignore_files_only: bool,
    ignore_gitignore: bool,
    gitignore_rules: List[str],
    ignore_patterns: tuple,
    writer: Callable[[str], None],
    use_xml: bool,
    use_json: bool,
    use_jsonl: bool,
    line_numbers: bool,
    regex_pattern: Optional[str],
    min_size: Optional[int],
    max_size: Optional[int],
    modified_after: Optional[datetime],
    first_json_entry: bool,
    dataset_mode: bool = False
) -> int:
    """Process a local path and print file contents based on filtering options."""
    if not os.path.exists(path):
        err_console.print(
            f"[error]Error processing {path}: "
            "No such file or directory[/error]"
        )
        return 1

    try:
        # If dataset_mode is on, print a quick tree overview
        if dataset_mode and os.path.isdir(path):
            print_repo_tree(writer, path, max_depth=1)

        if os.path.isfile(path):
            if should_include_file(
                path, extensions, regex_pattern, min_size, max_size, modified_after
            ):
                if not is_binary_file(path):
                    if dataset_mode:
                        print_file_summary(writer, path)
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    print_path(
                        writer,
                        path,
                        content,
                        use_xml,
                        use_json,
                        use_jsonl,
                        line_numbers,
                        dataset_mode
                    )
        else:
            for root, dirs, files in os.walk(path):
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith(".")]
                    files = [f for f in files if not f.startswith(".")]

                if not ignore_gitignore and gitignore_rules:
                    dirs[:] = [
                        d for d in dirs
                        if (
                            ignore_files_only or
                            not should_ignore(os.path.join(root, d), gitignore_rules)
                        )
                    ]
                    files = [
                        f for f in files
                        if not should_ignore(os.path.join(root, f), gitignore_rules)
                    ]

                if ignore_patterns:
                    if not ignore_files_only:
                        dirs[:] = [
                            d for d in dirs
                            if not any(
                                fnmatch(d, pattern) for pattern in ignore_patterns
                            )
                        ]
                    files = [
                        f for f in files
                        if not any(
                            fnmatch(f, pattern) for pattern in ignore_patterns
                        )
                    ]

                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    if should_include_file(
                        file_path,
                        extensions,
                        regex_pattern,
                        min_size,
                        max_size,
                        modified_after
                    ):
                        if not is_binary_file(file_path):
                            if dataset_mode:
                                print_file_summary(writer, file_path)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read()
                                print_path(
                                    writer,
                                    file_path,
                                    content,
                                    use_xml,
                                    use_json,
                                    use_jsonl,
                                    line_numbers,
                                    dataset_mode
                                )
                            except UnicodeDecodeError:
                                continue
    except Exception as e:
        err_console.print(
            f"[error]Error processing {path}: {str(e)}[/error]"
        )
        return 1

    return 0

def is_github_url(url: str) -> bool:
    return bool(re.match(GITHUB_URL_PATTERN, url))

def clone_github_repo(url: str) -> str:
    temp_dir = tempfile.mkdtemp(prefix=TEMP_DIR_PREFIX)
    try:
        Repo.clone_from(url, temp_dir)
        return temp_dir
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise click.ClickException(
            f"Failed to clone repository: {str(e)}"
        ) from e

def process_github_url(
    url: str,
    extensions: tuple,
    include_hidden: bool,
    ignore_files_only: bool,
    ignore_gitignore: bool,
    ignore_patterns: tuple,
    writer: Callable[[str], None],
    use_xml: bool,
    use_json: bool,
    use_jsonl: bool,
    line_numbers: bool,
    regex_pattern: Optional[str],
    min_size: Optional[int],
    max_size: Optional[int],
    modified_after: Optional[datetime],
    first_json_entry: bool,
    dataset_mode: bool = False
) -> None:
    try:
        temp_dir = clone_github_repo(url)
        try:
            rules = [] if ignore_gitignore else read_gitignore(temp_dir)
            process_local_path(
                temp_dir,
                extensions,
                include_hidden,
                ignore_files_only,
                ignore_gitignore,
                rules,
                ignore_patterns,
                writer,
                use_xml,
                use_json,
                use_jsonl,
                line_numbers,
                regex_pattern,
                min_size,
                max_size,
                modified_after,
                first_json_entry,
                dataset_mode=dataset_mode
            )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    except click.ClickException:
        raise
    except Exception as e:
        raise click.ClickException(
            f"Error processing GitHub repository: {str(e)}"
        ) from e

@click.command()
@click.argument("paths", nargs=-1, type=str)
@click.option(
    "-e", "--extension",
    "extensions",
    multiple=True,
    help="Filter by file extensions (e.g., -e py -e md)"
)
@click.option(
    "--include-hidden",
    is_flag=True,
    help="Include files and folders starting with ."
)
@click.option(
    "--ignore-files-only",
    is_flag=True,
    help="Apply --ignore option only to files"
)
@click.option(
    "--ignore-gitignore",
    is_flag=True,
    help="Ignore .gitignore files and include all files"
)
@click.option(
    "--ignore",
    "ignore_patterns",
    multiple=True,
    default=[],
    help="List of patterns to ignore"
)
@click.option(
    "--regex",
    "regex_pattern",
    help="Filter files using a regular expression pattern"
)
@click.option(
    "--min-size",
    type=click.INT,
    help="Filter files larger than size (in bytes)"
)
@click.option(
    "--max-size",
    type=click.INT,
    help="Filter files smaller than size (in bytes)"
)
@click.option(
    "--modified-after",
    type=click.DateTime(),
    help="Filter files modified after date (YYYY-MM-DD)"
)
@click.option(
    "-o", "--output",
    "output_file",
    type=click.Path(writable=True),
    help="Output to a file instead of stdout"
)
@click.option(
    "-c", "--cxml",
    "use_xml",
    is_flag=True,
    help="Output in Claude XML format"
)
@click.option(
    "-j", "--json",
    "use_json",
    is_flag=True,
    help="Output in JSON array format"
)
@click.option(
    "-l", "--jsonl",
    "use_jsonl",
    is_flag=True,
    help="Output in JSONL format (one JSON object per line)"
)
@click.option(
    "-n", "--line-numbers",
    is_flag=True,
    help="Add line numbers to the output"
)
@click.option(
    "--dataset-mode",
    is_flag=True,
    help="Enable special formatting & metadata for fine-tuning dataset prep"
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
    use_xml,
    use_json,
    use_jsonl,
    line_numbers,
    dataset_mode
):
    """Process and filter code from files and GitHub repositories.
    
    With --dataset-mode enabled, outputs a simplified repo tree (if path is a
    directory), provides short file summaries, and uses special delimiters.
    This is especially helpful when preparing fine-tuning datasets.
    """
    err_console.print("[info]🔍 ContextForge - Processing files...[/info]")

    # Validate regex pattern
    if regex_pattern:
        try:
            re.compile(regex_pattern)
        except re.error as e:
            err_console.print(f"[error]Invalid regex pattern: {regex_pattern}[/error]")
            raise click.ClickException(
                f"Invalid regex pattern: {regex_pattern}"
            ) from e

    if sum([use_xml, use_json, use_jsonl]) > 1:
        raise click.ClickException("Cannot use multiple output formats simultaneously")

    output_stream = None
    if output_file:
        output_stream = open(output_file, "w", encoding="utf-8")
        writer = output_stream.write
    else:
        def writer(s: str) -> None:
            click.echo(s, nl=False)

    if use_xml:
        writer("<documents>\n")
    elif use_json:
        writer("[\n")  # Start JSON array

    # Process each provided path
    first_json_entry = True
    for path in paths:
        # For local paths, if the path does not exist, raise an error.
        if not is_github_url(path) and not os.path.exists(path):
            msg = f"Error processing {path}: No such file or directory"
            raise click.ClickException(msg)
        try:
            if is_github_url(path):
                process_github_url(
                    path,
                    extensions,
                    include_hidden,
                    ignore_files_only,
                    ignore_gitignore,
                    ignore_patterns,
                    writer,
                    use_xml,
                    use_json,
                    use_jsonl,
                    line_numbers,
                    regex_pattern,
                    min_size,
                    max_size,
                    modified_after,
                    first_json_entry,
                    dataset_mode=dataset_mode
                )
            else:
                rules = [] if ignore_gitignore else read_gitignore(path)
                result = process_local_path(
                    path,
                    extensions,
                    include_hidden,
                    ignore_files_only,
                    ignore_gitignore,
                    rules,
                    ignore_patterns,
                    writer,
                    use_xml,
                    use_json,
                    use_jsonl,
                    line_numbers,
                    regex_pattern,
                    min_size,
                    max_size,
                    modified_after,
                    first_json_entry,
                    dataset_mode=dataset_mode
                )
                if result != 0:
                    raise click.ClickException(f"Error processing {path}")
            first_json_entry = False
        except click.ClickException as e:
            err_console.print(f"[error]{str(e)}[/error]")
            raise e

    if use_xml:
        writer("</documents>\n")
    elif use_json:
        writer("\n]\n")  # End JSON array

    if output_stream:
        output_stream.close()

    err_console.print("\n[success]✨ Processing complete![/success]")
    return 0

if __name__ == "__main__":
    cli()