"""Experiment registry and runners for the paper-ready workflow."""

from importlib import import_module

__all__ = [
    "INDEX_PATH",
    "context_for_spec",
    "load_index",
    "load_index_entries",
    "load_yaml",
    "resolve_spec_path",
    "run_spec",
    "spec_slug",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    run = import_module(".run", __name__)
    value = getattr(run, name)
    globals()[name] = value
    return value
