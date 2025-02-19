# ContextForge 🔍

[![PyPI](https://img.shields.io/pypi/v/contextforge.svg)](https://pypi.org/project/contextforge/)
[![Tests](https://github.com/yourusername/contextforge/actions/workflows/test.yml/badge.svg)](https://github.com/yourusername/contextforge/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/yourusername/contextforge/blob/master/LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/contextforge.svg)](https://pypi.org/project/contextforge/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> Modern code processing and filtering tool for AI training, code analysis, and documentation generation.

ContextForge is a powerful command-line tool that helps you process and filter code from local directories and GitHub repositories. It is perfect for preparing training data for AI models, conducting code analysis, and generating documentation.

## ✨ Features

- 🌐 **GitHub Integration**
  - Process repositories directly from URLs
  - Automatic cloning and cleanup
  - Respects `.gitignore` rules

- 🎯 **Smart Filtering**
  - File extensions (e.g., `.py`, `.js`, `.md`)
  - Regular expressions
  - File size constraints
  - Modification time filtering
  - Custom ignore patterns

- 🔍 **Intelligent Binary Detection**
  - Fast extension-based filtering
  - Magic number detection for file types
  - Git-style content heuristics
  - Handles common binary formats:
    - Images (PNG, JPG, GIF, etc.)
    - Documents (PDF, DOC, XLS)
    - Archives (ZIP, TAR, GZ)
    - Executables and Libraries

- 📄 **Flexible Output Formats**
  - Plain text with customizable separators
  - Claude-optimized XML format
  - JSON array format (`-j/--json`)
  - JSONL format (`-l/--jsonl`) for streaming
  - Line numbers support
  - File or stdout output

- 🛠️ **Developer Friendly**
  - Clean, intuitive CLI with rich console output
  - Comprehensive error handling
  - Memory-efficient processing
  - Extensive documentation

## 🚀 Installation

```bash
# Using pip
pip install contextforge

# Using uv (recommended)
uv pip install contextforge
```

## 💡 Quick Start

```bash
# Process a local directory
contextforge .

# Process a GitHub repository
contextforge https://github.com/flight505/example-repo

# Filter by file extensions
contextforge . -e py -e md

# Output as JSONL (recommended for large datasets)
contextforge . -l -o output.jsonl
```

## 📚 Usage Examples

### Advanced Filtering

```bash
# Find Python test files modified in the last week
contextforge . -e py --regex "test_.*\.py$" \
    --modified-after 2024-03-10

# Get all JavaScript files between 1KB and 1MB
contextforge . -e js --min-size 1024 --max-size 1048576

# Process specific files in a GitHub repo
contextforge https://github.com/flight505/example-repo \
    -e py --regex "src/.*controller\.py$"
```

### Output Options

```bash
# Generate Claude-optimized XML with line numbers
contextforge . --cxml -n -o output.xml

# Generate JSON array output
contextforge . -j -o output.json

# Generate JSONL (one JSON object per line)
contextforge . -l -o output.jsonl

# Process multiple paths with custom ignore patterns
contextforge src tests \
    --ignore "*.pyc" \
    --ignore "*/__pycache__/*" \
    --ignore-files-only
```

## 🎯 Common Use Cases

### AI Model Training

```bash
# Prepare training data in JSONL format
contextforge . -e py -l -o training.jsonl

# Extract documentation with XML format
contextforge . -e py -e md --cxml -o docs.xml
```

### Code Review

```bash
# Review recent changes in Python and JavaScript files
contextforge . --modified-after 2024-03-01 \
    --regex ".*\.(py|js)$" -n
```

### Documentation Generation

```bash
# Extract all markdown files, excluding node_modules
contextforge . --regex ".*\.md$" \
    --ignore "node_modules/*" -o docs.txt
```

### Repository Analysis

```bash
# Analyze specific files in a GitHub repository
contextforge https://github.com/flight505/example-repo \
    --regex ".*\.(py|js)$" \
    --min-size 1000 \
    --ignore "tests/*" \
    -n -o analysis.txt
```

## 🔧 Options

| Option | Description |
|--------|-------------|
| `-e, --extension` | Filter by file extensions |
| `--regex` | Filter using regex pattern |
| `--min-size` | Filter by minimum file size |
| `--max-size` | Filter by maximum file size |
| `--modified-after` | Filter by modification date |
| `--include-hidden` | Include hidden files |
| `--ignore` | Patterns to ignore |
| `--ignore-files-only` | Apply ignore patterns to files only |
| `--ignore-gitignore` | Ignore .gitignore rules |
| `-c, --cxml` | Output in Claude XML format |
| `-j, --json` | Output in JSON array format |
| `-l, --jsonl` | Output in JSONL format (one JSON per line) |
| `-n, --line-numbers` | Add line numbers |
| `-o, --output` | Write to file instead of stdout |

## 🤝 Contributing

Contributions are welcome! Here's how you can help:
1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Run tests: `pytest`
5. Submit a pull request

## 🔬 Development

```bash
# Clone the repository
git clone https://github.com/flight505/contextforge.git
cd contextforge

# Run directly with inline dependencies (recommended)
uv run contextforge.py

# Or install development dependencies
uv pip install -e ".[test]"

# Run tests
pytest
```

## 📝 License

This project is licensed under the Apache 2.0 License. See the LICENSE file for details.

<div align="center">
  <sub>Built with ❤️ for the modern developer ecosystem</sub>
</div>
```