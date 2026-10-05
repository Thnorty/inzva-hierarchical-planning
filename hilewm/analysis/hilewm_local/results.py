"""Save every measurement to disk, so that no reported number is stdout-only.

Added after an audit found three headline numbers that had been transcribed by
hand from terminal output, one of them from a snippet that no longer existed.
Wrap a script's entry point in `recorded_run` and it writes

* ``results/<script>/<timestamp>[_<tag>].json`` — the script name, timestamp,
  git commit (and whether the tree was dirty), every CLI argument, any
  structured metrics the script reported via `record()`, and the full printed
  output;
* one row in ``results/measurements.csv`` pointing at that file.

`record()` is a no-op when no run is active, so scripts can call it freely and
still be imported or run bare.

``results/runs.csv`` is separate and follows the schema CLAUDE.md prescribes for
*evaluation* runs (success rates from real rollouts). Diagnostic measurements
are not evaluation runs and go to ``measurements.csv`` instead.
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

__all__ = ["recorded_run", "record", "results_root"]

_REPO = Path(__file__).resolve().parents[2]
_active: "_Recorder | None" = None

MEASUREMENT_FIELDS = ["timestamp", "script", "tag", "git_commit", "git_dirty", "json_path", "headline"]


def results_root() -> Path:
    return _REPO / "results"


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=_REPO, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001 - recording must never break a measurement
        return ""


class _Tee(io.TextIOBase):
    def __init__(self, stream) -> None:
        self.stream = stream
        self.buffer_ = io.StringIO()

    def write(self, text: str) -> int:
        self.stream.write(text)
        self.buffer_.write(text)
        return len(text)

    def flush(self) -> None:
        self.stream.flush()


class _Recorder:
    def __init__(self, script: str, args: Any, tag: str) -> None:
        self.script = script
        self.tag = tag
        self.args = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()} if args else {}
        self.argv = list(sys.argv)          # the exact command, for re-running
        self.metrics: dict[str, Any] = {}
        self.headline = ""
        self.started = datetime.now()
        # Provenance is taken when the run *starts*: the code that ran is the code
        # at this commit. Reading it only at the end (as before 2026-09-22) could
        # stamp a record with a later commit if someone committed mid-run.
        self.commit_at_start = _git("rev-parse", "--short", "HEAD")
        self.dirty_at_start = bool(_git("status", "--porcelain", "--", "analysis", "code"))


def record(headline: str | None = None, **metrics: Any) -> None:
    """Attach structured metrics to the active run. No-op outside one."""
    if _active is None:
        return
    _active.metrics.update(metrics)
    if headline is not None:
        _active.headline = headline


@contextmanager
def recorded_run(script: str, args: Any = None, tag: str = "") -> Iterator[None]:
    global _active
    recorder = _Recorder(script, args, tag)
    tee = _Tee(sys.stdout)
    previous, _active = _active, recorder
    sys.stdout = tee
    try:
        yield
    finally:
        sys.stdout = tee.stream
        _active = previous
        _write(recorder, tee.buffer_.getvalue())


def _write(rec: _Recorder, output: str) -> None:
    try:
        stamp = rec.started.strftime("%Y%m%d-%H%M%S")
        safe_tag = "".join(c if c.isalnum() or c in "-_." else "_" for c in rec.tag)[:80]
        out_dir = results_root() / rec.script
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / (f"{stamp}_{safe_tag}.json" if safe_tag else f"{stamp}.json")

        commit, dirty = rec.commit_at_start, rec.dirty_at_start
        commit_at_end = _git("rev-parse", "--short", "HEAD")
        payload = {
            "script": rec.script,
            "tag": rec.tag,
            "timestamp": rec.started.isoformat(timespec="seconds"),
            "git_commit": commit,
            "git_dirty": dirty,
            "git_commit_at_end": commit_at_end,   # differs from git_commit if HEAD moved mid-run
            "argv": rec.argv,
            "args": rec.args,
            "headline": rec.headline,
            "metrics": rec.metrics,
            "stdout": output,
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str))

        index = results_root() / "measurements.csv"
        new = not index.exists()
        with index.open("a", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=MEASUREMENT_FIELDS)
            if new:
                writer.writeheader()
            writer.writerow({
                "timestamp": payload["timestamp"],
                "script": rec.script,
                "tag": rec.tag,
                "git_commit": commit,
                "git_dirty": dirty,
                "json_path": str(path.relative_to(_REPO)),
                "headline": rec.headline,
            })
        print(f"[results] saved {path.relative_to(_REPO)}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - never lose the measurement to a logging error
        print(f"[results] could not save run record: {exc!r}", file=sys.stderr)
