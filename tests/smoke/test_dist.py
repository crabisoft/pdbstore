import tarfile
import zipfile
from pathlib import Path
from sys import version_info

# pylint: disable=import-error, no-name-in-module
from build.__main__ import main as run_build

from pdbstore._version import __title__, __version__

DIST_DIR = Path("dist")
DOCS_DIR = "docs"
TEST_DIR = "tests"
SDIST_FILE = f"{__title__}-{__version__}.tar.gz"
WHEEL_FILE = f"{__title__.replace('-', '_')}-{__version__}-py{version_info.major}-none-any.whl"


def test_sdist_content():
    """test sdist content"""
    run_build(["--outdir", str(DIST_DIR.resolve()), "--sdist", "."])

    required_files = ["setup.py", "MANIFEST.in", "pyproject.toml"]
    required_files += ["README.rst", "COPYING", "AUTHORS.rst", "CHANGELOG.md"]

    required_dirs = [TEST_DIR]
    required_dirs = ["pdbstore/templates/html"]
    required_dirs += ["pdbstore/templates/json"]
    required_dirs += ["pdbstore/templates/markdown"]
    required_dirs += ["pdbstore/templates/text"]

    with tarfile.open(DIST_DIR / SDIST_FILE, "r:gz") as sdist:
        for path in required_files:
            test_file = sdist.getmember(f"{__title__}-{__version__}/{path}")
            assert test_file.isfile()
        for path in required_dirs:
            test_dir = sdist.getmember(f"{__title__}-{__version__}/{path}")
            assert test_dir.isdir()


def test_wheel_excludes_docs_and_tests():
    """test wheel content"""
    run_build(["--outdir", str(DIST_DIR.resolve()), "--wheel", "."])
    with zipfile.ZipFile(DIST_DIR / WHEEL_FILE) as wheel:
        assert not any(file.startswith((DOCS_DIR, TEST_DIR)) for file in wheel.namelist())
