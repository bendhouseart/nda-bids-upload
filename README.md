# Welcome to the DCAN Labs NDA BIDS Upload Repository

This repository is for taking data as BIDS and uploading it to an NDA collection.

The full documentation lives here: [ndabids.readthedocs.io](https://ndabids.readthedocs.io/)

## Quick Start

### Installation

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/DCAN-Labs/nda-bids-upload.git
cd nda-bids-upload

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

For detailed installation instructions, see [INSTALL.md](INSTALL.md).

### Usage

```bash
# Prepare data for NDA upload
python prepare.py -s <source_dir> -d <destination_dir>

# Or use the installed command
nda-prepare -s <source_dir> -d <destination_dir>
```

## Dependencies

This package includes:
- **[NDAR/manifest-data](https://github.com/NDAR/manifest-data)**: Git submodule providing the `nda_manifests.py` script
- **[bendhouseart/file-mapper](https://github.com/bendhouseart/file-mapper)**: Git dependency for file mapping operations
- Standard Python packages: mkdocs-material, PyYAML, pandas

All dependencies are managed via `pyproject.toml` for easy installation with `uv` or `pip`.
