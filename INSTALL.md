# Installation Guide

## Prerequisites

- Python 3.8 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git

## Installation

### Option 1: Using uv (Recommended)

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/DCAN-Labs/nda-bids-upload.git
cd nda-bids-upload

# Install the package with uv
uv pip install -e .
```

### Option 2: Using pip

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/DCAN-Labs/nda-bids-upload.git
cd nda-bids-upload

# Install the package with pip
pip install -e .
```

### Option 3: Development Setup with uv

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/DCAN-Labs/nda-bids-upload.git
cd nda-bids-upload

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

## Dependencies

This package includes the following dependencies (managed via `pyproject.toml`):

- **file-mapper**: The [bendhouseart/file-mapper](https://github.com/bendhouseart/file-mapper) repository for file mapping operations
- **manifest-data**: The [NDAR/manifest-data](https://github.com/NDAR/manifest-data) repository containing the `nda_manifests.py` script (included as git submodule)
- **mkdocs-material**: For documentation
- **PyYAML**: For YAML file processing
- **pandas**: For data manipulation

## Usage

After installation, you can use the tools:

```bash
# Run the prepare script
python prepare.py -s <source_dir> -d <destination_dir>

# Or if installed as a package
nda-prepare -s <source_dir> -d <destination_dir>
```

## Development

For development, install with dev dependencies:

```bash
uv pip install -e ".[dev]"
```

This will install additional development tools:
- pytest: For testing
- black: For code formatting
- flake8: For linting

## Updating Dependencies

To update the git submodule dependencies:

```bash
# Update manifest-data submodule
git submodule update --remote manifest-data

# Update file-mapper dependency (if needed)
uv pip install --upgrade git+https://github.com/bendhouseart/file-mapper.git
```

## Building and Publishing

To build the package:

```bash
uv build
```

To publish to PyPI:

```bash
uv publish
```

## Troubleshooting

If you encounter issues with dependencies:

1. Make sure the submodule is properly initialized:
   ```bash
   git submodule update --init --recursive
   ```

2. Check that the manifest-data directory exists:
   ```bash
   ls -la manifest-data/
   ```

3. Verify the nda_manifests.py file is present:
   ```bash
   ls -la manifest-data/nda_manifests.py
   ```

4. If using uv, try clearing the cache:
   ```bash
   uv cache clean
   ```
