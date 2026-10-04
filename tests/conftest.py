import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "tripo"
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def raw_bark():
    from biotile_geometry.rasterize import load_mesh, rasterize_mesh

    return rasterize_mesh(load_mesh(FIXTURES / "synthetic_bark.glb"), 256, seed=7)


@pytest.fixture(scope="session")
def raw_tafoni():
    from biotile_geometry.rasterize import load_mesh, rasterize_mesh

    return rasterize_mesh(load_mesh(FIXTURES / "synthetic_tafoni.glb"), 256, seed=7)
