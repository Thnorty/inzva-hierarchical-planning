# Eval results

Generated 2026-09-20 05:37 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/expC_results.txt`

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
| `gru_fine` | 0 | 10 | 1 | 10 | 50 | 300 | 30 | 36/50 = 72% | 16 |
| `gru_fine` | 1 | 10 | 1 | 10 | 50 | 300 | 30 | 39/50 = 78% | 15 |
| `gru_fine` | 2 | 10 | 1 | 10 | 50 | 300 | 30 | 30/50 = 60% | 17 |

## Full-protocol summary

3 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 70.0% |
| Std | 9.2 |
| Range | 60% to 78% |
| Pooled | 105/150 = 70.0% |

## Commands

Reproduce these runs with:

```bash
python scripts/plan/eval_wm.py --config-name inzva_gru_hier -m \
    policy=gru_fine seed=0,1,2
```
