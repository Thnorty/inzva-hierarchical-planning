# Eval results

Generated 2026-09-19 14:50 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/inzva_gru_coarse_results.txt`

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
| `gru_coarse` | 0 | 5 | 2 | 5 | 50 | 300 | 30 | 39/50 = 78% | 14 |
| `gru_coarse` | 1 | 5 | 2 | 5 | 50 | 300 | 30 | 38/50 = 76% | 14 |
| `gru_coarse` | 2 | 5 | 2 | 5 | 50 | 300 | 30 | 37/50 = 74% | 14 |

## Full-protocol summary

3 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 76.0% |
| Std | 2.0 |
| Range | 74% to 78% |
| Pooled | 114/150 = 76.0% |

## Commands

Reproduce these runs with:

```bash
python scripts/plan/eval_wm.py --config-name inzva_gru_coarse -m \
    policy=gru_coarse seed=0,1,2
```
