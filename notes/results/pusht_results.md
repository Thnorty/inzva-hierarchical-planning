# Eval results

Generated 2026-09-11 11:44 UTC by `scripts/collect_results.py`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/quentinll/pusht_results.txt`

## Environment

| | |
|---|---|
| commit (at collection) | `0751317` |
| torch | `2.11.0+cu128` |
| cuda | `12.8` |
| gpu | `NVIDIA GeForce RTX 3060 Laptop GPU` |
| transformers | `5.16.1` |

## Runs

| Policy | Seed | Episodes | Samples | CEM steps | Success | Seconds |
|--------|------|----------|---------|-----------|---------|---------|
| `quentinll/lewm-pusht` | 42 | 4 | 50 | 10 | 1/4 = 25% | 8 |
| `quentinll/lewm-pusht` | 42 | 10 | 300 | 30 | 9/10 = 90% | 42 |
| `quentinll/lewm-pusht` | 42 | 50 | 300 | 30 | 44/50 = 88% | 538 |

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
