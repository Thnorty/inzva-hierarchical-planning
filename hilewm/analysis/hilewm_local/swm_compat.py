"""Import `stable_worldmodel` submodules without running its package ``__init__``.

``import stable_worldmodel`` executes ``data/__init__.py``, which does an
unconditional ``from .formats.lance import LanceDataset`` -> ``import lancedb``.
The package pins ``lancedb>=0.30.0`` and the newest macOS x86_64 wheel is
0.25.3, so that import cannot succeed on an Intel Mac.

The parts we need never touch Lance. ``wm/lewm/module.py`` (``Predictor``,
``Embedder``, ``MLP``) and the whole ``solver`` subpackage depend only on torch,
numpy, gymnasium, einops and loguru. So we register synthetic package objects
for ``stable_worldmodel`` and each intermediate package, pointing their
``__path__`` at an extracted copy of the wheel. Python's normal import
machinery then resolves the leaf module and its relative imports, while the
real ``__init__`` files never run.

Resolution order:

1. a working ``stable_worldmodel`` install (this is what happens on Colab),
2. a previously extracted copy under ``analysis/.cache/``,
3. a fresh download of the wheel from PyPI -- extracted, never installed.

``stable-worldmodel`` is MIT licensed; the cache keeps the files verbatim and is
gitignored.
"""

from __future__ import annotations

import importlib
import importlib.util
import io
import json
import sys
import types
import urllib.request
import zipfile
from pathlib import Path
from types import ModuleType

__all__ = ["lewm_module", "cem_solver_class", "swm_submodule", "cache_dir", "clear_cache"]

_PYPI_JSON = "https://pypi.org/pypi/stable-worldmodel/json"
_ROOT_PACKAGE = "stable_worldmodel"
_ANALYSIS_ROOT = Path(__file__).resolve().parents[1]


def cache_dir() -> Path:
    """Directory holding the extracted third-party package."""
    return _ANALYSIS_ROOT / ".cache" / "swm_wheel"


def _download_and_extract(target: Path) -> Path:
    with urllib.request.urlopen(_PYPI_JSON, timeout=60) as response:
        meta = json.load(response)
    wheels = [u for u in meta["urls"] if u["filename"].endswith(".whl")]
    if not wheels:
        raise RuntimeError("no stable-worldmodel wheel found on PyPI")

    with urllib.request.urlopen(wheels[0]["url"], timeout=300) as response:
        payload = response.read()

    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [n for n in archive.namelist() if n.startswith(f"{_ROOT_PACKAGE}/")]
        archive.extractall(target, members=members)
    return target / _ROOT_PACKAGE


def ensure_package(*, allow_download: bool = True) -> Path:
    """Return the directory of an extracted ``stable_worldmodel`` package."""
    package_dir = cache_dir() / _ROOT_PACKAGE
    if (package_dir / "__init__.py").exists():
        return package_dir
    if not allow_download:
        raise RuntimeError(
            f"{package_dir} is missing and downloading is disabled. "
            "Either install stable-worldmodel or allow the download."
        )
    return _download_and_extract(cache_dir())


def _register_synthetic(name: str, path: Path) -> ModuleType:
    """Put a package object in ``sys.modules`` whose ``__init__`` never runs."""
    existing = sys.modules.get(name)
    if existing is not None and getattr(existing, "__hilewm_synthetic__", False):
        return existing
    package = types.ModuleType(name)
    package.__path__ = [str(path)]  # type: ignore[attr-defined]
    package.__package__ = name
    package.__hilewm_synthetic__ = True  # type: ignore[attr-defined]
    sys.modules[name] = package
    return package


def swm_submodule(dotted: str, *, allow_download: bool = True, prefer_installed: bool = True) -> ModuleType:
    """Import ``dotted`` (e.g. ``stable_worldmodel.solver.cem``) safely."""
    if not dotted.startswith(f"{_ROOT_PACKAGE}."):
        raise ValueError(f"{dotted!r} is not inside {_ROOT_PACKAGE}")

    if dotted in sys.modules:
        return sys.modules[dotted]

    if prefer_installed:
        try:
            return importlib.import_module(dotted)
        except Exception:  # noqa: BLE001 - fall back to the extracted copy
            for name in list(sys.modules):
                if name == _ROOT_PACKAGE or name.startswith(f"{_ROOT_PACKAGE}."):
                    if not getattr(sys.modules[name], "__hilewm_synthetic__", False):
                        del sys.modules[name]

    package_dir = ensure_package(allow_download=allow_download)

    # Register every package on the path so that no real __init__ executes.
    parts = dotted.split(".")
    _register_synthetic(_ROOT_PACKAGE, package_dir)
    for depth in range(1, len(parts) - 1):
        name = ".".join(parts[: depth + 1])
        _register_synthetic(name, package_dir.joinpath(*parts[1 : depth + 1]))

    return importlib.import_module(dotted)


def lewm_module(*, allow_download: bool = True, prefer_installed: bool = True) -> ModuleType:
    """Module holding ``Predictor``, ``Embedder`` and ``MLP``."""
    return swm_submodule(
        f"{_ROOT_PACKAGE}.wm.lewm.module",
        allow_download=allow_download,
        prefer_installed=prefer_installed,
    )


def cem_solver_class(*, allow_download: bool = True, prefer_installed: bool = True):
    """The planner's actual ``CEMSolver``, so diagnostics search as it does."""
    module = swm_submodule(
        f"{_ROOT_PACKAGE}.solver.cem",
        allow_download=allow_download,
        prefer_installed=prefer_installed,
    )
    return module.CEMSolver


def clear_cache() -> None:
    import shutil

    if cache_dir().exists():
        shutil.rmtree(cache_dir())
