import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

FIXTURES = REPO / "tests" / "fixtures"


@pytest.fixture
def cs2settings_fixture_dir() -> Path:
    return FIXTURES / "cs2settings"


@pytest.fixture
def repo_root() -> Path:
    return REPO
