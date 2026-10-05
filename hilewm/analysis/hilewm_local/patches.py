"""Opt-in runtime fixes for defects that stop the artifact from running.

Nothing here edits a file under `code/`. Each fix is a monkeypatch applied
explicitly by our own entry points, so it is easy to see, easy to remove, and
easy to retire if an upstream release fixes the same thing.

Currently five fixes and one deliberate override.

**`CEMSolver` derives the environment count from the first info-dict value.**

```python
total_envs = len(next(iter(info_dict.values())))   # solver/cem.py:131
```

The comment above that line says the count is taken from the info dict *so that
callers can solve for a subset of envs*, which is a reasonable design. But
`_plan_high` and `_plan_low` put the string `planner_level` first
(`h_le_wm/planning/policies.py:793`, `:840`, `:954`), so the count becomes
`len("high") == 4` or `len("low") == 3` whatever the real env count is. The
solver then returns a plan for 4 envs and `_plan_high`'s `reshape(n_envs, ...)`
raises for every `n_envs != 4`. Verified against the real
`HierarchicalWorldModelPolicy` on 2026-09-19: `n_envs=4` succeeds by
coincidence, while 1, 8 and 50 all fail.

The artifact's own `EmpiricalMacroActionSolver` does it correctly -- it uses
`self.n_envs` and slices only tensors -- so the empirical-macro path is
unaffected and only the plain-CEM path is broken.

The fix reorders the incoming info dict so a tensor comes first. It leaves the
solver's arithmetic untouched and preserves the upstream "subset of envs"
intent, because the count still comes from the rows actually passed in. The
`planner_level` string is still sliced to a fragment, but `HiJEPA.get_cost`
already falls back to routing on tensor keys when that happens
(`h_le_wm/models/jepa.py:543-551`).

**The eval path does not register the legacy pickle module aliases.**

The released `*_object.ckpt` files are pickled model objects referencing the old
top-level module names `hi_jepa`, `hi_module`, `hi_vq`, `hi_waypoint_sampling`
and `module`. `h_le_wm/train/hierarchical.py:41-54` maps all five onto
`h_le_wm.models.*` with `sys.modules.setdefault`, but
`h_le_wm/eval/hierarchical.py:34-39` only touches `_baseline_adapter.ARPredictor`
and never registers the rest. So `swm.policy.AutoCostModel` -> `torch.load` raises
`ModuleNotFoundError: No module named 'hi_jepa'` and **the shipped eval cannot
load the shipped checkpoints**. Verified on Colab 2026-09-26.

**`World.evaluate_from_dataset` does not exist in the released library.**

`h_le_wm/eval/hierarchical.py:562` calls

```python
world.evaluate_from_dataset(dataset, start_steps=..., goal_offset_steps=...,
                            eval_budget=..., episodes_idx=..., callables=...,
                            video_path=...)
```

`stable_worldmodel` 0.1.1 has no such method. It exposes the same behaviour
through `World.evaluate(dataset=..., episodes_idx=..., start_steps=...,
goal_offset=..., eval_budget=..., callables=..., video=...)`, which dispatches to
the private `_evaluate_from_dataset` (`world/world.py:188-255`, `:492`). Two
keywords were renamed on the way: `goal_offset_steps` -> `goal_offset` and
`video_path` -> `video`.

`apply_world_evaluate_alias` adds the missing method as a thin forwarder, so the
artifact's call site runs unchanged and the evaluation itself is the library's.

**`world.history_size` must be present for the artifact and absent for the library.**

`swm.World` forwards unknown kwargs to `gym.make`, and 0.1.1's `PushT` accepts
neither `history_size` nor `frame_skip`, so the eval config's `world` block crashes
it. Deleting the two keys fixes the eval -- and breaks the artifact's own acting
diagnostics, which *read* one of them:
`shape_prefix = (world.num_envs, eval_cfg.world.history_size)`
(`scripts/diagnostics/hi_acting_diagnostics.py:393`). The two requirements are
mutually exclusive, so no config can satisfy both and the fix has to be at runtime.

`apply_world_env_kwargs_filter` wraps `World.__init__` and drops those keys on the way
to `gym.make`, leaving the config intact for whoever reads it. Both are no-ops in
0.1.1 at their configured values of 1: that version has no frame stacking and no frame
skipping.

**The acting diagnostics drive the world through an API 0.1.1 does not have.**

`scripts/diagnostics/hi_acting_diagnostics.py` steps the environment itself rather
than going through `World.evaluate`, and it assumes a gymnasium vector env:

```python
for i, env in enumerate(ctx.world.envs.unwrapped.envs):    # :440
world.step()                                               # :1089
world.envs.unwrapped._autoreset_envs = np.zeros(...)        # :1091
```

In 0.1.1 `World.envs` is a custom `EnvPool` with no `unwrapped`, and `World` has no
public `step` at all — only the private `_run` / `_run_iter` generator. So the whole
acting-diagnostics surface, including the `oracle_subgoal_acting` experiment the
paper's own reproduction workflow runs, cannot execute against the released library.

`apply_world_step_shim` adds the two missing pieces:

* `EnvPool.unwrapped` returns the pool itself, which is what gymnasium's `unwrapped`
  means for something that is not a wrapper. The `_autoreset_envs` assignment then
  lands harmlessly on the pool -- and it is a no-op by nature here, since `EnvPool.step`
  does not auto-reset anything (`world/env_pool.py:118-142`).
* `World.step` performs exactly the two statements `_run_iter` executes per iteration
  (`world/world.py:398-404`) and **does not reset**, which is precisely what the
  diagnostic's `_autoreset_envs = 0` line was trying to arrange. Terminated envs keep
  being stepped; the diagnostic's loop ORs `terminateds` across steps, so the success
  rate is unaffected, while the *final* latent of an env that already succeeded keeps
  drifting -- read `final_terminal_latent_error_mean` with that in mind.

`register_object_ckpt_aliases` fixes it the artifact's own way: importing
`h_le_wm.train.hierarchical` runs that registration as an import side effect. If
that import fails, the five aliases are registered directly as a fallback, in the
same order (`module` last, since it points at the dynamic
`_baseline_lewm_module` that `baseline_adapter` creates).
"""

from __future__ import annotations

import numpy as np
import torch

from .swm_compat import cem_solver_class

__all__ = [
    "apply_acting_max_steps_override",
    "apply_cem_env_count_fix",
    "apply_world_env_kwargs_filter",
    "apply_world_step_shim",
    "apply_world_evaluate_alias",
    "is_cem_env_count_fix_needed",
    "register_object_ckpt_aliases",
]

_LEGACY_ALIASES = {
    "hi_jepa": "h_le_wm.models.jepa",
    "hi_module": "h_le_wm.models.latent_action",
    "hi_vq": "h_le_wm.models.vq",
    "hi_waypoint_sampling": "h_le_wm.models.waypoint_sampling",
}


def register_object_ckpt_aliases() -> str:
    """Make `torch.load` able to unpickle the released `*_object.ckpt` files.

    Returns which route was taken: "already", "train-module" or "fallback".
    """
    import importlib
    import sys

    if "hi_jepa" in sys.modules:
        return "already"

    try:
        # Registers all five aliases as an import side effect, including the
        # dynamic `module` -> `_baseline_lewm_module` mapping.
        importlib.import_module("h_le_wm.train.hierarchical")
        if "hi_jepa" in sys.modules:
            return "train-module"
    except Exception as exc:  # noqa: BLE001 - fall back rather than fail the run
        print(f"[hilewm_local] h_le_wm.train.hierarchical import failed ({exc!r}); "
              "registering aliases directly", flush=True)

    for alias, target in _LEGACY_ALIASES.items():
        sys.modules.setdefault(alias, importlib.import_module(target))
    try:
        import h_le_wm.baseline.adapter as _adapter

        _ = _adapter.ARPredictor  # creates `_baseline_lewm_module`
        baseline_module = sys.modules.get("_baseline_lewm_module")
        if baseline_module is not None:
            sys.modules.setdefault("module", baseline_module)
    except Exception as exc:  # noqa: BLE001
        print(f"[hilewm_local] baseline adapter unavailable ({exc!r}); the "
              "`module` alias is not registered", flush=True)
    return "fallback"

_FLAG = "__hilewm_env_count_fixed__"


def _tensors_first(info_dict: dict) -> dict:
    if not info_dict:
        return info_dict
    first = next(iter(info_dict.values()))
    if torch.is_tensor(first) or isinstance(first, np.ndarray):
        return info_dict
    ordered = {k: v for k, v in info_dict.items() if torch.is_tensor(v) or isinstance(v, np.ndarray)}
    if not ordered:
        return info_dict
    ordered.update({k: v for k, v in info_dict.items() if k not in ordered})
    return ordered


def is_cem_env_count_fix_needed(solver_class=None) -> bool:
    """True when the installed solver still derives the count from any value."""
    import inspect

    solver_class = solver_class or cem_solver_class()
    if getattr(solver_class, _FLAG, False):
        return False
    try:
        source = inspect.getsource(solver_class.solve)
    except (OSError, TypeError):
        return True
    return "len(next(iter(info_dict.values())))" in source


def apply_cem_env_count_fix(*, force: bool = False) -> bool:
    """Patch ``CEMSolver.solve`` to see a tensor first. Returns True if applied."""
    solver_class = cem_solver_class()
    if getattr(solver_class, _FLAG, False):
        return False
    if not force and not is_cem_env_count_fix_needed(solver_class):
        return False

    original = solver_class.solve

    def solve(self, info_dict: dict, init_action=None):
        return original(self, _tensors_first(info_dict), init_action)

    solve.__doc__ = original.__doc__
    solve.__wrapped__ = original  # type: ignore[attr-defined]
    solver_class.solve = solve
    setattr(solver_class, _FLAG, True)
    return True


def apply_world_evaluate_alias(*, force: bool = False) -> bool:
    """Add `World.evaluate_from_dataset`, which the artifact calls and 0.1.1 lacks.

    Returns True if the alias was installed, False if the library already has the
    method (in which case nothing is touched).
    """
    import stable_worldmodel as swm

    world_class = swm.World
    if hasattr(world_class, "evaluate_from_dataset") and not force:
        return False

    def evaluate_from_dataset(
        self,
        dataset,
        *,
        episodes_idx=None,
        start_steps=None,
        goal_offset_steps=None,
        goal_offset=None,
        eval_budget=None,
        callables=None,
        video_path=None,
        video=None,
        reset_mode=None,
    ):
        # The artifact's names on the left, the library's on the right.
        return self.evaluate(
            dataset=dataset,
            episodes_idx=episodes_idx,
            start_steps=start_steps,
            goal_offset=goal_offset if goal_offset is not None else goal_offset_steps,
            eval_budget=eval_budget,
            callables=callables,
            video=video if video is not None else video_path,
            reset_mode=reset_mode,
        )

    world_class.evaluate_from_dataset = evaluate_from_dataset
    return True


_WORLD_KWARGS_FLAG = "_hilewm_local_env_kwargs_filtered"
UNSUPPORTED_WORLD_KWARGS = ("history_size", "frame_skip")


def apply_world_env_kwargs_filter(
    *, drop: tuple[str, ...] = UNSUPPORTED_WORLD_KWARGS, force: bool = False
) -> tuple[str, ...]:
    """Stop `World` forwarding kwargs `PushT` rejects, without touching the config.

    Returns the keys the filter will drop, or () if it was already installed.
    """
    import stable_worldmodel as swm

    world_class = swm.World
    if getattr(world_class, _WORLD_KWARGS_FLAG, False) and not force:
        return ()

    original_init = world_class.__init__

    def __init__(self, *args, **kwargs):  # noqa: N807 - patching a dunder
        dropped = [key for key in drop if key in kwargs]
        for key in dropped:
            kwargs.pop(key)
        if dropped:
            print(f"[hilewm_local] World: dropped env kwargs {dropped} "
                  "(no-ops in stable-worldmodel 0.1.1, which PushT rejects)", flush=True)
        return original_init(self, *args, **kwargs)

    world_class.__init__ = __init__
    setattr(world_class, _WORLD_KWARGS_FLAG, True)
    return tuple(drop)


def apply_world_step_shim(*, force: bool = False) -> tuple[str, ...]:
    """Give `World` a public `step` and `EnvPool` an `unwrapped`, for the diagnostics.

    Returns the names installed, or () when the library already provides them.
    """
    import stable_worldmodel as swm
    from stable_worldmodel.world.env_pool import EnvPool

    installed: list[str] = []
    world_class = swm.World

    if force or not hasattr(world_class, "step"):
        def step(self):
            # The two statements _run_iter runs per iteration (world/world.py:398-404),
            # without the reset: the caller decides what happens to terminated envs.
            actions = self._get_actions()
            (
                _,
                self.rewards,
                self.terminateds,
                self.truncateds,
                self.infos,
            ) = self.envs.step(actions, mask=None)
            return self.infos

        world_class.step = step
        installed.append("World.step")

    if force or not hasattr(EnvPool, "unwrapped"):
        # Not a wrapper, so `unwrapped` is itself -- the gymnasium contract.
        EnvPool.unwrapped = property(lambda self: self)
        installed.append("EnvPool.unwrapped")

    return tuple(installed)


def apply_acting_max_steps_override(max_steps: int | None = None,
                                    *, factor: float | None = None) -> str | None:
    """Override the step budget the acting diagnostics hardcode. Not a compatibility fix.

    `run_oracle_subgoal_acting` and `run_generated_subgoal_acting` call
    `run_world_loop(..., max_steps=int(cfg.goal_offset_steps))`
    (`hi_acting_diagnostics.py:1166`, `:1354`), so at d=50 the agent gets exactly 50
    environment steps to cover a 50-step goal -- no slack at all, and `--eval-budget`
    does not touch it (only `online_hierarchical_logging` reads that, `:1480`).

    The paper's own goal budget at d=50 is 100 steps, twice the goal distance, and it
    reports a higher oracle success rate than we measured at 50. This override exists to
    test whether that difference is the budget. **A run using it is not the authors'
    configuration**, so it prints what it did and the caller must record it.

    Returns a description of the override, or None when nothing was requested.
    """
    if max_steps is None and factor is None:
        return None
    if max_steps is not None and factor is not None:
        raise ValueError("pass max_steps or factor, not both")

    import hi_acting_diagnostics as diagnostics

    original = getattr(diagnostics, "_hilewm_original_run_world_loop",
                       diagnostics.run_world_loop)
    diagnostics._hilewm_original_run_world_loop = original

    def patched(ctx, batch, policy, *, max_steps: int, **kwargs):
        replacement = int(round(max_steps * factor)) if factor is not None else int(max_steps_override)
        print(f"[hilewm_local] acting loop: max_steps {max_steps} -> {replacement} "
              "(deliberate override, NOT the authors' configuration)", flush=True)
        return original(ctx, batch, policy, max_steps=replacement, **kwargs)

    max_steps_override = max_steps
    diagnostics.run_world_loop = patched
    return (f"max_steps={max_steps}" if max_steps is not None
            else f"max_steps x{factor}")
