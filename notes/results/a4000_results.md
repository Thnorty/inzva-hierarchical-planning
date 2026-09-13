# Eval results

Generated 2026-09-12 23:58 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/quentinll/a4000_results.txt`

## Environment

| | |
|---|---|
| commit (at collection) | `8a3fe3a` |
| torch | `2.11.0+cu130` |
| cuda | `13.0` |
| gpu | `NVIDIA RTX A4000` |
| transformers | `5.16.1` |

## Runs

| Policy | Seed | Episodes | Samples | CEM steps | Success | Seconds |
|--------|------|----------|---------|-----------|---------|---------|
| `quentinll/lewm-pusht` | 0 | 50 | 300 | 30 | 42/50 = 84% | 78 |
| `quentinll/lewm-pusht` | 1 | 50 | 300 | 30 | 47/50 = 94% | 77 |
| `quentinll/lewm-pusht` | 2 | 50 | 300 | 30 | 42/50 = 84% | 81 |

## Full-protocol summary

3 runs at 50 episodes, 300 samples, 30 CEM steps.

| | |
|---|---|
| Mean | 87.3% |
| Std | 5.8 |
| Range | 84% to 94% |
| Pooled | 131/150 = 87.3% |

## Commands

The shared config, three seeds:

```bash
python scripts/plan/eval_wm.py --config-name inzva_pusht -m \
    policy=quentinll/lewm-pusht seed=0,1,2
```

A single run at the upstream config (needs the `+`, see README §7):

```bash
python scripts/plan/eval_wm.py \
    policy=quentinll/lewm-pusht +plan_config.history_len=3
```
