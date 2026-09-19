# Eval results

Generated 2026-09-19 14:48 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/inzva_gru_results.txt`

## Environment

| | |
|---|---|
| commit (at collection) | `40e11f2` |
| torch | `2.11.0+cu130` |
| cuda | `13.0` |
| gpu | `NVIDIA RTX A4000` |
| transformers | `5.16.1` |

## Runs

| Policy | Seed | Horizon | Block | Recede | Episodes | Samples | CEM steps | Success | Seconds |
|--------|------|---------|-------|--------|----------|---------|-----------|---------|---------|
| `gru_fine` | 0 | 10 | 1 | 10 | 50 | 300 | 30 | 36/50 = 72% | 15 |
| `gru_fine` | 1 | 10 | 1 | 10 | 50 | 300 | 30 | 37/50 = 74% | 16 |
| `gru_fine` | 2 | 10 | 1 | 10 | 50 | 300 | 30 | 31/50 = 62% | 17 |

## Full-protocol summary

3 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 69.3% |
| Std | 6.4 |
| Range | 62% to 74% |
| Pooled | 104/150 = 69.3% |

## Commands

Reproduce these runs with:

```bash
python scripts/plan/eval_wm.py --config-name inzva_gru -m \
    policy=gru_fine seed=0,1,2
```
