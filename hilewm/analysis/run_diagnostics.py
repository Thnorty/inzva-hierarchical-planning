"""Run the artifact's acting diagnostics with our runtime fixes applied.

The artifact ships exactly the experiment our diagnosis plan calls step 5 and never
got: `oracle_subgoal_acting` feeds the **expert's own future waypoint latents** to the
low-level planner as subgoals and reports a success rate. That is the upper bound the
whole hierarchy is competing against, and it is the number that decides how to read
our result that Hi-LeWM-C (34.0 %) does not beat plain CEM (36.0 %): if the oracle is
far above both, the high level is the binding constraint and better subgoals should
pay; if the oracle is near them, nothing the high level does can matter much, which
would explain why neither of the paper's two fixes shows up in control.

The diagnostics entry point is not `h_le_wm.eval.hierarchical`, so
`analysis/run_eval.py` does not cover it. This wrapper applies the same three fixes
and works around a fourth problem specific to this path.

    python analysis/run_diagnostics.py --policy runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15 \\
        --experiment-kind oracle_subgoal_acting --device cuda --num-eval 50 \\
        --save-json out.json --append-tsv out.tsv

Every argument is passed straight through to
`code/scripts/diagnostics/run_hi_acting_diagnostic.py`; see its `--help`. One flag is
ours and is stripped before theirs sees it:

    --max-steps N    run the acting loop for N environment steps

The oracle and generated experiments hardcode `max_steps = goal_offset_steps`
(`hi_acting_diagnostics.py:1166`, `:1354`), so at d=50 the agent gets exactly 50 steps
for a 50-step goal and `--eval-budget` cannot change it. The paper's own goal budget at
d=50 is 100. **A run with `--max-steps` is not the authors' configuration** and must be
recorded as such; the override prints itself at the top of the run.

**Why the fourth and fifth fixes.** This script loads `h_le_wm/config/eval/hi_pusht.yaml`
directly and hands `cfg.world` to `swm.World` (`hi_acting_diagnostics.py:280`), which
forwards the `world.history_size` / `world.frame_skip` keys 0.1.1's `PushT` rejects.
Deleting them from the config is what `run_eval.py` does with Hydra — and it does not
work here, because the diagnostic itself *reads* one of them:
`shape_prefix = (world.num_envs, eval_cfg.world.history_size)`
(`hi_acting_diagnostics.py:393`). Present for the artifact, absent for the library:
mutually exclusive, so the fix is `apply_world_env_kwargs_filter`, which drops them
inside `World.__init__` and leaves the config alone.

The diagnostics then step the environment themselves through an API 0.1.1 does not
have -- `world.envs.unwrapped.envs` and `world.step()`, both gymnasium vector-env
assumptions, against a `World` whose `envs` is a custom `EnvPool` and which has no
public `step`. `apply_world_step_shim` supplies both, faithfully: see its docstring in
`hilewm_local/patches.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (_REPO_ROOT / "code", _REPO_ROOT / "analysis",
              _REPO_ROOT / "code" / "scripts" / "diagnostics"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

DEFAULT_EVAL_CONFIG = _REPO_ROOT / "code" / "h_le_wm" / "config" / "eval" / "hi_pusht.yaml"


def main() -> int:
    from hilewm_local.patches import (
        apply_acting_max_steps_override,
        apply_cem_env_count_fix,
        apply_world_env_kwargs_filter,
        apply_world_evaluate_alias,
        apply_world_step_shim,
        is_cem_env_count_fix_needed,
        register_object_ckpt_aliases,
    )

    print(f"[hilewm_local] CEM env-count fix: needed={is_cem_env_count_fix_needed()} "
          f"applied={apply_cem_env_count_fix()}", flush=True)
    print(f"[hilewm_local] object-checkpoint module aliases: {register_object_ckpt_aliases()}",
          flush=True)
    print(f"[hilewm_local] World.evaluate_from_dataset alias installed: "
          f"{apply_world_evaluate_alias()}", flush=True)
    print(f"[hilewm_local] World env-kwargs filter: {apply_world_env_kwargs_filter() or 'already installed'}",
          flush=True)
    print(f"[hilewm_local] World/EnvPool step shim: {apply_world_step_shim() or 'already present'}",
          flush=True)

    # Our own flags, stripped before the artifact's parser sees them.
    argv = list(sys.argv[1:])
    override_steps = None
    if "--max-steps" in argv:
        index = argv.index("--max-steps")
        override_steps = int(argv[index + 1])
        del argv[index:index + 2]
    if not any(arg == "--eval-config" or arg.startswith("--eval-config=") for arg in argv):
        # Their default is a path relative to cwd; make it absolute so the wrapper
        # works from anywhere. The file is used unmodified.
        argv += ["--eval-config", str(DEFAULT_EVAL_CONFIG)]

    if override_steps is not None:
        # Import the diagnostics module first, so the override has something to patch.
        import hi_acting_diagnostics  # noqa: F401
        print(f"[hilewm_local] acting max_steps override: "
              f"{apply_acting_max_steps_override(override_steps)}", flush=True)

    import run_hi_acting_diagnostic as runner

    sys.argv = ["run_hi_acting_diagnostic.py", *argv]
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
