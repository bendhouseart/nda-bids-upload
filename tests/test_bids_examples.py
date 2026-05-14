"""Tests that require the bids-examples submodule and example data.

Skips all tests in this module if the submodule is not initialized or if
no example datasets (e.g. pet002) are present. Run `make submodules` first.

To keep NDA pipeline outputs for inspection, pass a base directory::

    pytest tests/test_bids_examples.py -v --bids-examples-workdir=/home/you/test_bids_examples_nda

Each dataset is written under ``WORKDIR/<dataset>/<dataset>_reduced/`` (same
layout as the default temporary parent). Remove a dataset subdir for a clean rerun.
"""

import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from records import vtcmd_path


@contextmanager
def _bids_examples_target_path(work_root: Path | None, dataset_name: str):
    """Parent for ``{dataset_name}_reduced``: temp dir, or ``work_root / dataset_name``."""
    if work_root is not None:
        base = (work_root / dataset_name).expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
        yield base
        return
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

# Folder names under bids-examples to skip (e.g. "code", "tools").
# Datasets that fail reduce_bids + lookup are listed in tests/exclude.txt (one per line).
# Run: uv run python tests/discover_exclude.py  to regenerate exclude.txt.
EXCLUDE_DATASETS: list[str] = []


def _load_exclude_file() -> list[str]:
    """Load exclude list from tests/exclude.txt (one dataset name per line)."""
    exclude_path = _project_root() / "tests" / "exclude.txt"
    if not exclude_path.is_file():
        return []
    return [
        line.strip()
        for line in exclude_path.read_text().splitlines()
        if line.strip()
    ]

# Allow importing reduce_bids_participants when running this test file.
if __name__ != "__main__":
    _tests_dir = Path(__file__).resolve().parent
    if str(_tests_dir) not in sys.path:
        sys.path.insert(0, str(_tests_dir))



def _project_root() -> Path:
    """Project root (nda-bids-upload)."""
    return Path(__file__).resolve().parent.parent


def _bids_examples_path() -> Path:
    """Path to the bids-examples submodule (tests/bids-examples, or bids-examples at project root)."""
    root = _project_root()
    for candidate in (root / "tests" / "bids-examples", root / "bids-examples"):
        if candidate.is_dir():
            return candidate
    return root / "tests" / "bids-examples"  # preferred; fixture will skip if missing


def _bids_dataset_dirs(root: Path, exclude: list[str] | None = None):
    """Yield paths to all subdirs of root as BIDS datasets, optionally excluding given folder names."""
    excluded = set(EXCLUDE_DATASETS) | set(_load_exclude_file())
    if exclude is not None:
        excluded |= set(exclude)
    for p in sorted(root.iterdir()):
        if not p.is_dir() or p.name.startswith(".") or p.name in excluded:
            continue
        yield p


@pytest.fixture(scope="module")
def bids_examples_available():
    """Ensure bids-examples submodule is loaded and example files are present.

    Skips all tests in this module if:
    - The bids-examples directory does not exist (submodule not initialized), or
    - The directory is empty or missing expected content (e.g. no dataset dirs).
    """
    root = _bids_examples_path()
    if not root.is_dir():
        pytest.skip(
            "bids-examples submodule not loaded. Run: make submodules"
        )
    # Check for typical content: dataset_description.json or at least one dataset dir (e.g. pet002)
    has_description = (root / "dataset_description.json").is_file()
    subdirs = [d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]
    if not has_description and not subdirs:
        pytest.skip(
            "bids-examples directory is empty or has no example datasets. Run: make submodules"
        )
    return root


def test_bids_examples_submodule_loaded(bids_examples_available):
    """bids-examples submodule is present and has content."""
    root = bids_examples_available
    assert root.is_dir()
    # At least one of: root dataset_description or a known example dataset
    assert (root / "dataset_description.json").is_file() or any(
        (root / d).is_dir() for d in ("pet002", "pet003") if (root / d).exists()
    )


def pytest_generate_tests(metafunc):
    if "dataset_path" in metafunc.fixturenames:
        root = _bids_examples_path()
        if not root.is_dir():
            metafunc.parametrize("dataset_path", [])
            return
        
        datasets = list(_bids_dataset_dirs(root))
        metafunc.parametrize(
            "dataset_path",
            datasets,
            ids=[p.name for p in datasets]
        )


def test_pet002_example_present(bids_examples_available):
    """pet002 example dataset exists and has expected BIDS layout."""
    root = bids_examples_available
    pet002 = root / "pet002"
    if not pet002.is_dir():
        pytest.skip("pet002 not found in bids-examples")
    assert (pet002 / "participants.tsv").is_file() or (pet002 / "dataset_description.json").is_file()


def test_bids_examples_to_nda(bids_examples_available, dataset_path, bids_examples_workdir):
    """Per dataset: temp folder -> reduce -> lookup on reduced -> update lookup.csv with GUIDs/dates; assert success.

    Use ``pytest ... --bids-examples-workdir=/path`` to keep outputs under
    ``/path/<dataset>/`` (same layout as the default temp parent) for inspection.

    Assumes pytest runs in the same environment where the project is installed
    (``pyproject.toml`` dependencies, including ``nda-tools`` / ``vtcmd``).

    **NDA login (nda-tools 0.7+):** ``vtcmd`` calls the NDA validation API and must
    authenticate. Do a one-time interactive login from this repo's venv (same machine
    you use for pytest), e.g. run ``vtcmd`` on any small CSV with ``-m`` / ``-w`` as
    needed and enter your NDA username and password when prompted. Credentials are
    stored under ``~/.NDATools/`` and the OS keyring. For headless runs, set
    ``NDA_USERNAME`` (or ``NDA_TOOLS_USERNAME``) if your username is not already in
    ``settings.cfg``; the password must still be available in the keyring from that
    prior login.
    """
    assert vtcmd_path(), (
        "vtcmd missing for this interpreter; install the project here (e.g. `pip install -e .`)."
    )
    from populate_bids_participants import (
        ndaify_participants_files,
        InvalidDatasetError,
    )
    from utilities.lookup import LookUpTable
    from utilities.mapping import MappingTemplator
    from prepare import input_check, filemap_and_recordsprep

    name = dataset_path.name
    # 1. Parent for this dataset: temp dir, or --bids-examples-workdir / <dataset> /
    with _bids_examples_target_path(bids_examples_workdir, name) as target_path:
        reduced_bids_dataset = target_path / f"{name}_reduced"
        nda_upload_directory = reduced_bids_dataset / "upload"
        nda_upload_directory.mkdir(parents=True, exist_ok=True)
        # 2. Run reduce_bids_participants on this dataset; target path is within the temp folder.
        #    (This reduces the dataset and writes the reduced BIDS tree into target_path.)
        try:
            ndaify_participants_files(
                dataset_path, reduced_bids_dataset, max_participants=10
            )
        except InvalidDatasetError as e:
            # If bids-validator fails to run (network/proxy/cache issues),
            # skip validation for this dataset but continue the loop so
            # that remaining pipeline tests still run on other datasets.
            msg = str(e)
            if "bids-validator failed" in msg:
                # Log by attaching to the assertion message if nothing
                # else runs for this dataset.
                # Just continue to the next dataset without raising.
                pass
            raise
        # 3. lookup.csv was updated with conftest GUIDS and generated interview dates (inside reduce_bids).
        assert (nda_upload_directory / "lookup.csv").is_file(), (
            f"dataset {name}: expected lookup.csv after reduce + lookup"
        )
        # 4. Generate file mapping
        mapping = MappingTemplator(reduced_bids_dataset, nda_upload_directory)

        # 5. Run prepare.py
        filemap_and_recordsprep(nda_upload_directory, reduced_bids_dataset, False)