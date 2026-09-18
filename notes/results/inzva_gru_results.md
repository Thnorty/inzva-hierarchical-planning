# Eval results

Generated 2026-09-18 05:09 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/inzva_gru_results.txt`

## Environment

| | |
|---|---|
| commit (at collection) | `2c9ff91` |
| torch | `2.11.0+cu130` |
| cuda | `13.0` |
| gpu | `NVIDIA RTX A4000` |
| transformers | `5.16.1` |

## Runs

| Policy | Seed | Episodes | Samples | CEM steps | Success | Seconds |
|--------|------|----------|---------|-----------|---------|---------|
| `gru_fine` | 0 | 50 | 300 | 30 | 5/50 = 10% | 62 |
| `gru_fine` | 1 | 50 | 300 | 30 | 11/50 = 22% | 62 |
| `gru_fine` | 2 | 50 | 300 | 30 | 7/50 = 14% | 62 |

## Full-protocol summary

3 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 15.3% |
| Std | 6.1 |
| Range | 10% to 22% |
| Pooled | 23/150 = 15.3% |

## Commands

Reproduce these runs with:

```bash
python scripts/plan/eval_wm.py --config-name inzva_gru -m \
    policy=gru_fine seed=0,1,2
```
