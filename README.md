# ContextForge 🔍

[![PyPI](https://img.shields.io/pypi/v/contextforge.svg)](https://pypi.org/project/contextforge/)
[![Tests](https://github.com/yourusername/contextforge/actions/workflows/test.yml/badge.svg)](https://github.com/yourusername/contextforge/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/yourusername/contextforge/blob/master/LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/contextforge.svg)](https://pypi.org/project/contextforge/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> Modern code processing and filtering tool for AI training, code analysis, and documentation generation.

ContextForge is a powerful command-line tool that helps you process and filter code from local directories and GitHub repositories. Perfect for preparing training data for AI models, conducting code analysis, and generating documentation.

## ✨ Features

- 🌐 **GitHub Integration**
  - Process repositories directly from URLs
  - Automatic cloning and cleanup
  - Respects .gitignore rules

- 🎯 **Smart Filtering**
  - File extensions (e.g., .py, .js, .md)
  - Regular expressions
  - File size constraints
  - Modification time filtering
  - Custom ignore patterns

- 📄 **Flexible Output**
  - Plain text with customizable separators
  - Claude-optimized XML format
  - Line numbers support
  - File or stdout output

- 🛠️ **Developer Friendly**
  - Clean, intuitive CLI
  - Rich console output
  - Comprehensive error handling
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

# Process multiple paths with custom ignore patterns
contextforge src tests \
    --ignore "*.pyc" \
    --ignore "*/__pycache__/*" \
    --ignore-files-only
```

## 🎯 Common Use Cases

### AI Model Training

```bash
# Prepare training data from multiple file types
contextforge . -e py -e js -e ts --cxml -o training.xml
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

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
uv pip install -e ".[test]"

# Run tests
pytest

# Run linting
ruff check .
```

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

<div align="center">
  <sub>Built with ❤️ for the modern developer ecosystem</sub>
</div>
