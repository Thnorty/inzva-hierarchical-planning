# Eval results

Generated 2026-09-20 05:39 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/inzva_gru_hier_results.txt`

## Environment

| | |
|---|---|
| commit (at collection) | `0a88e1a` |
| torch | `2.11.0+cu130` |
| cuda | `13.0` |
| gpu | `NVIDIA RTX A4000` |
| transformers | `5.16.1` |

## Runs

| Policy | Seed | Horizon | Block | Recede | Episodes | Samples | CEM steps | Success | Seconds |
|--------|------|---------|-------|--------|----------|---------|-----------|---------|---------|
| `gru_fine` | 0 | 10 | 1 | 10 | 50 | 300 | 30 | 39/50 = 78% | 14 |
| `gru_fine` | 1 | 10 | 1 | 10 | 50 | 300 | 30 | 41/50 = 82% | 13 |
| `gru_fine` | 2 | 10 | 1 | 10 | 50 | 300 | 30 | 34/50 = 68% | 15 |

## Full-protocol summary

3 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 76.0% |
| Std | 7.2 |
| Range | 68% to 82% |
| Pooled | 114/150 = 76.0% |

## Commands

Reproduce these runs with:

```bash
python scripts/plan/eval_wm.py --config-name inzva_gru_hier -m \
    policy=gru_fine seed=0,1,2
```
