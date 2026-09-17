# Eval results

Generated 2026-09-17 12:32 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/dinowm_romer_results.txt`

## Environment

| | |
|---|---|
| commit (at collection) | `34613f8` |
| torch | `2.11.0+cu130` |
| cuda | `13.0` |
| gpu | `NVIDIA RTX A4000` |
| transformers | `5.16.1` |

## Runs

| Policy | Seed | Episodes | Samples | CEM steps | Success | Seconds |
|--------|------|----------|---------|-----------|---------|---------|
| `dinowm_kotmul_adapted` | 0 | 50 | 300 | 30 | 45/50 = 90% | 16225 |
| `dinowm_kotmul_adapted` | 1 | 50 | 300 | 30 | 41/50 = 82% | 18364 |
| `dinowm_kotmul_adapted` | 2 | 50 | 300 | 30 | 40/50 = 80% | 18039 |

## Full-protocol summary

3 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 84.0% |
| Std | 5.3 |
| Range | 80% to 90% |
| Pooled | 126/150 = 84.0% |

## Commands

Reproduce these runs with:

```bash
python scripts/plan/eval_wm.py --config-name inzva_dinowm -m \
    policy=dinowm_kotmul_adapted seed=0,1,2
```
