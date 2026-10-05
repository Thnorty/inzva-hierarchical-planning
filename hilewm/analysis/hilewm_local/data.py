"""Read the PushT HDF5 dataset without ``stable_worldmodel``.

`h_le_wm/planning/policies.py` imports nothing from `stable_worldmodel` — only
numpy, torch and torchvision — so `calibrate_latent_prior` and
`build_empirical_macro_action_bank` can be called directly on any object that
offers the small slice of the dataset API they touch: `get_col_data`,
`column_names`, and optionally per-row episode metadata. :class:`HDF5Columns`
provides exactly that, so our measurements run the authors' own code rather
than a reimplementation of it.

Layout, per `stable_worldmodel/data/formats/hdf5.py`: the file holds one
root-level dataset per column plus `ep_len` and `ep_offset`, and rows are a flat
concatenation over episodes.

Verified against the real file on 2026-09-19: `pusht_expert_train.h5` holds
18685 episodes over 2336736 rows and *does* carry `episode_idx` and `step_idx`
columns, so `_try_get_episode_metadata` finds them and chunk sampling respects
episode boundaries. Every column present in the file is passed through, which
is what keeps our numbers identical to the planner's.

``hide_episode_metadata=True`` withholds those two columns, which forces the
artifact's `_sample_valid_chunk_starts` down its no-metadata fallback and lets
chunks straddle episode boundaries. That is a counterfactual for measuring what
the boundary check buys, not the default -- say so when reporting it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

__all__ = ["HDF5Columns", "build_action_scaler", "write_episode_subset"]

_META_COLUMNS = ("ep_len", "ep_offset")
_EPISODE_COLUMNS = ("episode_idx", "step_idx", "ep_idx")


class HDF5Columns:
    """Minimal read-only view over a stable-worldmodel HDF5 dataset."""

    def __init__(
        self,
        path: str | Path,
        *,
        hide_episode_metadata: bool = False,
        cache: bool = True,
    ) -> None:
        import h5py  # imported here so the module loads without h5py

        # The `pixels` column is written with a compression filter that HDF5
        # only knows about once hdf5plugin has registered it; without this a
        # read raises "can't open directory .../plugin". Action and state
        # columns are uncompressed and read fine either way, so this is a soft
        # dependency.
        try:
            import hdf5plugin  # noqa: F401
        except ModuleNotFoundError:
            pass

        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)
        self._h5py = h5py
        self._file = h5py.File(self.path, "r", swmr=True, rdcc_nbytes=256 * 1024 * 1024)
        self._cache_enabled = cache
        self._cache: dict[str, np.ndarray] = {}

        self.ep_len = np.asarray(self._file["ep_len"][:])
        self.ep_offset = np.asarray(self._file["ep_offset"][:])
        hidden = set(_EPISODE_COLUMNS) if hide_episode_metadata else set()
        self.hidden_columns = sorted(hidden & set(self._file.keys()))
        self._columns = [
            k for k in self._file.keys() if k not in _META_COLUMNS and k not in hidden
        ]

    # -- dataset API consumed by the artifact -------------------------------

    @property
    def column_names(self) -> list[str]:
        return list(self._columns)

    def get_col_data(self, col: str) -> np.ndarray | None:
        if col not in self._columns:
            return None
        if col in self._cache:
            return self._cache[col]
        data = np.asarray(self._file[col][:])
        if self._cache_enabled:
            self._cache[col] = data
        return data

    def get_row_data(self, row_idx: Any, columns: list[str] | None = None) -> dict[str, np.ndarray]:
        """Read selected rows. Name `columns` to avoid pulling `pixels` along."""
        wanted = self._columns if columns is None else [c for c in columns if c in self._columns]
        return {col: np.asarray(self._file[col][row_idx]) for col in wanted}

    # -- convenience --------------------------------------------------------

    @property
    def num_episodes(self) -> int:
        return int(len(self.ep_len))

    @property
    def num_rows(self) -> int:
        return int(self.ep_len.sum())

    def column_shape(self, col: str) -> tuple[int, ...]:
        return tuple(self._file[col].shape)

    def describe(self) -> str:
        rows = [f"{self.path.name}: {self.num_episodes} episodes, {self.num_rows} rows"]
        if self.hidden_columns:
            rows.append(f"  (hiding {', '.join(self.hidden_columns)})")
        for col in self._columns:
            dset = self._file[col]
            rows.append(f"  {col:12s} {tuple(dset.shape)}  {dset.dtype}")
        return "\n".join(rows)

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> HDF5Columns:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def build_action_scaler(dataset: HDF5Columns):
    """Reproduce the action normaliser the eval pipeline fits.

    `h_le_wm/eval/hierarchical.py::build_process_map` fits a scikit-learn
    ``StandardScaler`` per cached column after dropping rows with NaNs. The
    prior calibration and the empirical bank both apply it, so anything we
    compare against them must use the same transform.
    """
    from sklearn import preprocessing

    action = dataset.get_col_data("action")
    if action is None:
        raise ValueError(f"{dataset.path} has no 'action' column")
    action = np.asarray(action)
    action = action[~np.isnan(action).any(axis=1)]
    scaler = preprocessing.StandardScaler()
    scaler.fit(action)
    return {"action": scaler}


def write_episode_subset(
    source: str | Path,
    target: str | Path,
    *,
    num_episodes: int = 200,
    seed: int = 0,
    columns: list[str] | None = None,
) -> Path:
    """Copy whole episodes into a smaller HDF5 file.

    Episodes are kept intact so that anything trajectory-based stays valid, and
    `ep_len`/`ep_offset` are rebuilt for the subset. Dropping `pixels` shrinks
    the PushT file from ~46 GB to a few hundred MB, which is enough for every
    action-space analysis.
    """
    import h5py

    source, target = Path(source), Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(source, "r") as src:
        ep_len = np.asarray(src["ep_len"][:])
        ep_offset = np.asarray(src["ep_offset"][:])
        available = [k for k in src.keys() if k not in _META_COLUMNS]
        keep = columns if columns is not None else available
        missing = sorted(set(keep) - set(available))
        if missing:
            raise ValueError(f"columns not in {source.name}: {missing}")

        rng = np.random.default_rng(seed)
        count = min(int(num_episodes), len(ep_len))
        chosen = np.sort(rng.choice(len(ep_len), size=count, replace=False))

        row_index = np.concatenate(
            [np.arange(ep_offset[e], ep_offset[e] + ep_len[e], dtype=np.int64) for e in chosen]
        )
        new_len = ep_len[chosen]
        new_offset = np.concatenate(([0], np.cumsum(new_len)[:-1])).astype(ep_offset.dtype)

        with h5py.File(target, "w") as dst:
            dst.create_dataset("ep_len", data=new_len)
            dst.create_dataset("ep_offset", data=new_offset)
            for col in keep:
                src_dset = src[col]
                shape = (len(row_index),) + src_dset.shape[1:]
                out = dst.create_dataset(col, shape=shape, dtype=src_dset.dtype)
                # h5py fancy indexing needs sorted, chunked reads to stay fast.
                step = 4096
                for start in range(0, len(row_index), step):
                    idx = row_index[start : start + step]
                    out[start : start + len(idx)] = src_dset[idx]

    return target
