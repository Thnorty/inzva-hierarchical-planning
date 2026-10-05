"""The paper's CEM budgets, as the single source of truth for every script.

Written after we ran d=50 goal offsets with d=25's iteration count for two days
without noticing: the scripts took 1500 samples from Table 5's d=50 row and 20
iterations from the shipped `config/eval/hi_pusht.yaml`, whose high-level
settings (900/20) correspond to d=25. The authors' own d=50 diagnostics
(`h_le_wm/experiments/pusht_diagnostics.py`) use 40.

So the budget is now derived from the goal offset. Scripts declare their CEM
arguments with ``default=None`` and call `apply_budget`, which fills in the
Table 5 row for ``args.goal_offset`` and leaves any value the caller passed
explicitly alone. The resolved budget, and which fields were overridden, go into
every results record — a run at a non-paper budget is visible as such.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from typing import Any

__all__ = ["Budget", "PAPER_TABLE_5", "paper_budget", "add_budget_args", "apply_budget"]


@dataclass(frozen=True)
class Budget:
    high_samples: int
    high_steps: int
    high_topk: int
    low_samples: int
    low_steps: int
    low_topk: int
    eval_budget: int  # environment steps allowed per episode


# Paper Table 5, PushT. High level / low level: samples, steps, top-k.
PAPER_TABLE_5: dict[int, Budget] = {
    25: Budget(900, 20, 10, 300, 30, 150, 50),
    50: Budget(1500, 40, 10, 900, 30, 150, 100),
    75: Budget(1200, 60, 10, 1200, 30, 150, 150),
}

# argparse dest -> Budget field. Scripts may declare any subset.
_ARG_FIELDS = {
    "num_samples": "high_samples",
    "n_steps": "high_steps",
    "topk": "high_topk",
    "low_samples": "low_samples",
    "low_steps": "low_steps",
    "low_topk": "low_topk",
}


def paper_budget(goal_offset: int) -> Budget:
    try:
        return PAPER_TABLE_5[int(goal_offset)]
    except KeyError:
        raise ValueError(
            f"no Table 5 budget for goal offset {goal_offset}; the paper defines {sorted(PAPER_TABLE_5)}. "
            "Pass every CEM argument explicitly to run at another offset."
        ) from None


def add_budget_args(parser: argparse.ArgumentParser, *, low: bool = False, goal_offset: int = 50) -> None:
    """Declare --goal-offset and the CEM arguments, all defaulting to Table 5."""
    parser.add_argument("--goal-offset", type=int, default=goal_offset,
                        help=f"goal offset d; selects the Table 5 budget (one of {sorted(PAPER_TABLE_5)})")
    parser.add_argument("--num-samples", type=int, default=None, help="high-level CEM samples (default: Table 5)")
    parser.add_argument("--n-steps", type=int, default=None, help="high-level CEM iterations (default: Table 5)")
    parser.add_argument("--topk", type=int, default=None, help="high-level CEM elites (default: Table 5)")
    if low:
        parser.add_argument("--low-samples", type=int, default=None, help="low-level CEM samples (default: Table 5)")
        parser.add_argument("--low-steps", type=int, default=None, help="low-level CEM iterations (default: Table 5)")
        parser.add_argument("--low-topk", type=int, default=None, help="low-level CEM elites (default: Table 5)")


def apply_budget(args: argparse.Namespace) -> dict[str, Any]:
    """Fill unset CEM arguments from Table 5. Returns what was used, for recording."""
    budget = paper_budget(args.goal_offset)
    table = asdict(budget)
    overridden: dict[str, Any] = {}
    for dest, field in _ARG_FIELDS.items():
        if not hasattr(args, dest):
            continue
        value = getattr(args, dest)
        if value is None:
            setattr(args, dest, table[field])
        elif value != table[field]:
            overridden[dest] = {"used": value, "table_5": table[field]}
    resolved = {dest: getattr(args, dest) for dest in _ARG_FIELDS if hasattr(args, dest)}
    note = "paper Table 5" if not overridden else f"Table 5 with overrides: {sorted(overridden)}"
    print(f"budget     : d={args.goal_offset} -> {note}: "
          + ", ".join(f"{k}={v}" for k, v in resolved.items()))
    return {"goal_offset": args.goal_offset, "source": note, "resolved": resolved,
            "overridden": overridden, "table_5_row": table}
