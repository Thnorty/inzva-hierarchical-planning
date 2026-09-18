# Eval results

Generated 2026-09-18 05:20 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/gru_h10_results.txt`

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
| `gru_fine` | 0 | 50 | 300 | 30 | 29/50 = 58% | 23 |
| `gru_fine` | 1 | 50 | 300 | 30 | 31/50 = 62% | 23 |
| `gru_fine` | 2 | 50 | 300 | 30 | 30/50 = 60% | 23 |

## Full-protocol summary

3 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 60.0% |
| Std | 2.0 |
| Range | 58% to 62% |
| Pooled | 90/150 = 60.0% |

## Commands

Reproduce these runs with:

```bash
python scripts/plan/eval_wm.py --config-name inzva_gru -m \
    policy=gru_fine seed=0,1,2
```
