# Experiment A: success rate against planning budget

Generated 2026-10-06 17:03 UTC by `scripts/sweep.py collect`.
Do not edit by hand; rerun the script instead.

Source: `$STABLEWM_HOME/checkpoints/expA_{flat,coarse,hier}_results.txt`

## Environment

| | |
|---|---|
| commit (at collection) | `ed4bb49` |
| torch | `2.11.0+cu130` |
| cuda | `13.0` |
| gpu | `NVIDIA RTX A4000` |

Seeds 0, 1, 2, 3, 4, 50 episodes each, so 250 episodes per cell. CEM: 30 iterations, top 10% kept. Compute is model transition evaluations per plan.

## Success rate

| Planner | Samples | Compute / plan | Seeds | Mean | Std | Pooled | 95% interval | Seconds / run |
|---|---|---|---|---|---|---|---|---|
| Flat CEM, fine model | 25 | 7,500 | 48, 50, 48, 48, 40 | 46.8% | 3.9 | 117/250 | 40.7 to 53.0 | 16 |
| Flat CEM, fine model | 50 | 15,000 | 62, 60, 48, 52, 48 | 54.0% | 6.6 | 135/250 | 47.8 to 60.1 | 15 |
| Flat CEM, fine model | 100 | 30,000 | 60, 72, 56, 58, 60 | 61.2% | 6.3 | 153/250 | 55.0 to 67.0 | 15 |
| Flat CEM, fine model | 300 | 90,000 | 72, 78, 62, 64, 60 | 67.2% | 7.6 | 168/250 | 61.2 to 72.7 | 16 |
| Flat CEM, fine model | 600 | 180,000 | 70, 74, 54, 66, 64 | 65.6% | 7.5 | 164/250 | 59.5 to 71.2 | 19 |
| Coarse model alone | 25 | 3,750 | 50, 54, 44, 54, 42 | 48.8% | 5.6 | 122/250 | 42.7 to 55.0 | 15 |
| Coarse model alone | 50 | 7,500 | 60, 70, 56, 50, 46 | 56.4% | 9.3 | 141/250 | 50.2 to 62.4 | 14 |
| Coarse model alone | 100 | 15,000 | 70, 78, 62, 64, 56 | 66.0% | 8.4 | 165/250 | 59.9 to 71.6 | 14 |
| Coarse model alone | 300 | 45,000 | 78, 74, 74, 70, 70 | 73.2% | 3.3 | 183/250 | 67.4 to 78.3 | 14 |
| Coarse model alone | 600 | 90,000 | 76, 76, 72, 72, 72 | 73.6% | 2.2 | 184/250 | 67.8 to 78.7 | 16 |
| Ours, coarse then fine (k = 2) | 25 | 7,615 | 46, 54, 48, 60, 48 | 51.2% | 5.8 | 128/250 | 45.0 to 57.3 | 15 |
| Ours, coarse then fine (k = 2) | 50 | 11,365 | 56, 70, 54, 52, 50 | 56.4% | 7.9 | 141/250 | 50.2 to 62.4 | 15 |
| Ours, coarse then fine (k = 2) | 100 | 18,865 | 70, 78, 60, 64, 58 | 66.0% | 8.1 | 165/250 | 59.9 to 71.6 | 14 |
| Ours, coarse then fine (k = 2) | 300 | 48,865 | 78, 82, 68, 66, 60 | 70.8% | 9.0 | 177/250 | 64.9 to 76.1 | 15 |
| Ours, coarse then fine (k = 2) | 600 | 93,865 | 74, 84, 76, 70, 66 | 74.0% | 6.8 | 185/250 | 68.2 to 79.0 | 16 |

## Paired differences

Same seed, same episodes. Only-A and only-B are the episodes one planner solved and the other did not. The last rows match compute instead of samples: coarse at n samples costs exactly what flat costs at n / 2.

| A | B | A - B, points | Only A | Only B | McNemar p |
|---|---|---|---|---|---|
| hier at 25 (7,615) | flat at 25 (7,500) | +4.4 | 25 | 14 | 0.108 |
| hier at 25 (7,615) | coarse at 25 (3,750) | +2.4 | 12 | 6 | 0.238 |
| coarse at 25 (3,750) | flat at 25 (7,500) | +2.0 | 22 | 17 | 0.522 |
| hier at 50 (11,365) | flat at 50 (15,000) | +2.4 | 23 | 17 | 0.43 |
| hier at 50 (11,365) | coarse at 50 (7,500) | +0.0 | 11 | 11 | 1 |
| coarse at 50 (7,500) | flat at 50 (15,000) | +2.4 | 23 | 17 | 0.43 |
| hier at 100 (18,865) | flat at 100 (30,000) | +4.8 | 28 | 16 | 0.0961 |
| hier at 100 (18,865) | coarse at 100 (15,000) | +0.0 | 14 | 14 | 1 |
| coarse at 100 (15,000) | flat at 100 (30,000) | +4.8 | 32 | 20 | 0.126 |
| hier at 300 (48,865) | flat at 300 (90,000) | +3.6 | 24 | 15 | 0.2 |
| hier at 300 (48,865) | coarse at 300 (45,000) | -2.4 | 9 | 15 | 0.307 |
| coarse at 300 (45,000) | flat at 300 (90,000) | +6.0 | 31 | 16 | 0.04 |
| hier at 600 (93,865) | flat at 600 (180,000) | +8.4 | 35 | 14 | 0.0038 |
| hier at 600 (93,865) | coarse at 600 (90,000) | +0.4 | 14 | 13 | 1 |
| coarse at 600 (90,000) | flat at 600 (180,000) | +8.0 | 31 | 11 | 0.00289 |
| coarse at 50 (7,500) | flat at 25 (7,500) | +9.6 | 36 | 12 | 0.000717 |
| coarse at 100 (15,000) | flat at 50 (15,000) | +12.0 | 48 | 18 | 0.000287 |
| coarse at 600 (90,000) | flat at 300 (90,000) | +6.4 | 34 | 18 | 0.0365 |

## Commands

```bash
python scripts/sweep.py run
python scripts/sweep.py collect
```
