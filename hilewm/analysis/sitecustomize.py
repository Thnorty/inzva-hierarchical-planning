"""Apply our runtime fixes to subprocesses that we do not launch ourselves.

The artifact's shell scripts go through `h_le_wm/experiments/run.py`, which
spawns `python -m h_le_wm.eval.hierarchical` as a subprocess. `analysis/run_eval.py`
cannot reach those, so this file offers the other route: Python imports a
`sitecustomize` module automatically at startup if one is on the path, which
gives us a hook into every interpreter that starts with `analysis/` on
`PYTHONPATH`.

It is **off unless asked for**. Set `HILEWM_PATCH_CEM=1` to enable it:

    export PYTHONPATH="$PWD/code:$PWD/analysis:${PYTHONPATH:-}"
    export HILEWM_PATCH_CEM=1
    bash scripts/run_pusht_smoke.sh

Prefer `analysis/run_eval.py` where you control the command; it is explicit and
prints what it did. Use this only for the scripted paths.

Any failure here is swallowed, because a raising `sitecustomize` would break
every Python process in the environment.
"""

from __future__ import annotations

import os
import sys

if os.environ.get("HILEWM_PATCH_CEM") == "1":
    try:
        from hilewm_local.patches import apply_cem_env_count_fix

        if apply_cem_env_count_fix():
            print("[hilewm_local] CEM env-count fix applied via sitecustomize", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - never break interpreter startup
        print(f"[hilewm_local] sitecustomize patch skipped: {exc!r}", file=sys.stderr)
