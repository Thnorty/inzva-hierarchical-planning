"""Run the artifact's hierarchical eval with our runtime fixes applied.

Drop-in replacement for

    python -m h_le_wm.eval.hierarchical --config-name=hi_pusht ...

Use

    python analysis/run_eval.py --config-name=hi_pusht ...

with the same Hydra arguments. It applies
`hilewm_local.patches.apply_cem_env_count_fix` and then hands control to the
artifact's own `run()`, so the evaluation itself is unmodified.

Without that fix the hierarchical planner cannot run at any environment count:
`CEMSolver` reads the env count off the first info-dict value, which the
artifact sets to the string `planner_level`, so the high level always plans for
`len("high") == 4` envs and the low level for `len("low") == 3`. Verified on
2026-09-19 against the real policy -- `n_envs` of 1, 4, 8 and 50 all raise, since
no single value satisfies both levels.

It also registers the legacy pickle module aliases (`hi_jepa`, `hi_module`,
`hi_vq`, `hi_waypoint_sampling`, `module`). The artifact registers those in
`h_le_wm/train/hierarchical.py` but not in `h_le_wm/eval/hierarchical.py`, so the
shipped eval cannot unpickle the shipped `*_object.ckpt` files -- it stops with
`ModuleNotFoundError: No module named 'hi_jepa'`.

It also adds `World.evaluate_from_dataset`, which the artifact calls and the
released library does not define; the alias forwards to `World.evaluate` with the
two renamed keywords mapped back.

Every fix is a no-op when the installed library already behaves correctly, so this
wrapper degrades into the module it wraps.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (_REPO_ROOT / "code", _REPO_ROOT / "analysis"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))


def main() -> None:
    from hilewm_local.patches import (
        apply_cem_env_count_fix,
        apply_world_evaluate_alias,
        is_cem_env_count_fix_needed,
        register_object_ckpt_aliases,
    )

    needed = is_cem_env_count_fix_needed()
    applied = apply_cem_env_count_fix()
    print(f"[hilewm_local] CEM env-count fix: needed={needed} applied={applied}", flush=True)

    # Without this the eval cannot load the released checkpoints at all: they are
    # pickled objects naming `hi_jepa` and friends, and only the *train* module
    # registers those aliases (`h_le_wm/train/hierarchical.py:41-54`), not the eval
    # one.
    route = register_object_ckpt_aliases()
    print(f"[hilewm_local] object-checkpoint module aliases: {route}", flush=True)

    # `World.evaluate_from_dataset` is called by the artifact and does not exist in
    # stable-worldmodel 0.1.1; the alias forwards to `World.evaluate`.
    aliased = apply_world_evaluate_alias()
    print(f"[hilewm_local] World.evaluate_from_dataset alias installed: {aliased}", flush=True)

    # Imported after the patch so the solver class is already corrected, and
    # lazily so that --help works without a full stable_worldmodel install.
    from h_le_wm.eval.hierarchical import run

    run()


if __name__ == "__main__":
    main()
