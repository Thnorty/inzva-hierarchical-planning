# Status report

Hierarchical coarse-to-fine planning on PushT, built on `stable-worldmodel`.

Written 2026-09-13. This is a snapshot for the team. `INZVA_README.md` is the
manual and stays the source of truth for how to do anything; this file says
where we are and what is left.

---

## 1. The goal

**Claim under test: planning at two time scales beats planning at one, when the
compute budget is small.**

A flat planner searches every step of a 40-step horizon. Ours plans 5 coarse
waypoints at a stride of `k = 8`, then fills in between them. If the claim
holds, the hierarchy reaches the same success rate with far fewer model
evaluations, and the gap widens as the budget shrinks.

Three systems are compared, all on PushT, all under one evaluation protocol:

| Row | World model | Planner | Purpose |
|-----|-------------|---------|---------|
| 1 | DINO-WM | CEM | Published reference point |
| 2 | Our GRU | CEM (flat) | The baseline we must beat |
| 3 | Our GRU | Coarse + fine, hierarchical | The contribution |

Three experiments:

- **A** — rows 2 against 3 across compute budgets. This is the actual claim.
- **B** — rows 1 against 3 across factors of variation. Generality.
- **C** — set `k = 1` and the hierarchy must collapse to row 2's score. A
  correctness check on the implementation, not a result. **Run it first**: if it
  fails, A and B mean nothing.

---

## 2. Where we are

**Infrastructure is finished. The research has not started.**

Everything needed to run and trust an experiment exists and is verified on three
machines. Not one line of the hierarchical method has been written yet.

| | |
|---|---|
| Baseline of record | **87.3%** (LeWM + CEM, 3 seeds, shared protocol) |
| Reproducibility | Measured on 3 machines, at most 2 episodes of 150 differ |
| Our world model | **Not written** |
| Our solver | **Not written** |
| Experiments run | **None** |

### What is done

- **Protocol locked.** `scripts/plan/config/inzva_pusht.yaml` fixes episode
  count, budget, goal offset, resolution and seeds. Changing it invalidates
  every comparison, so nobody edits it alone.
- **Reproduction closed.** The published 96% is not reproducible. Every
  mechanical explanation was tested and eliminated. Our number is 87.3% +/- 7.6
  over three seeds, and that is the baseline we compare against.
- **Three machines agree.** Windows RTX 3060, TRUBA V100, Ubuntu RTX A4000. No
  pair disagrees by more than 2 episodes in 150; all three means within 0.6
  points. Records are in `notes/results/`.
- **TRUBA is set up and working** (`INZVA_README.md` section 12), with job
  scripts in `slurm/` and a CPU preflight that catches a broken environment in
  about a minute instead of after a half-day queue.
- **Decisions locked** (section 6.5): `k = 8`, `horizon = 40`,
  `action_block = 1`, 224px everywhere, one encoder shared between coarse and
  fine and then frozen.

### What is not done

Everything that makes this a research project rather than a test harness.

---

## 3. What is left, in blocking order

### 3.1 Write the method (blocks everything)

Six files, none of which exist:

| File | What it is |
|------|-----------|
| `models/gru_wm.py` | The fine GRU world model. Everything else depends on it |
| `scripts/train_gru.py` | Its training loop |
| `models/gru_coarse.py` | The coarse model, stride `k` |
| `solver/hierarchical.py` | The coarse-to-fine solver. The contribution |
| `scripts/sweep.py` | Budget sweep driver for Experiment A |
| `README.md` | Write-up |

`models/gru_wm.py` and `scripts/train_gru.py` are the critical path. Nothing can
be evaluated until the fine model trains.

It has to satisfy the `Dynamics` protocol in `stable_worldmodel/protocols.py`
(`encode` and `rollout`) or the existing planner cannot call it.

### 3.2 Run Experiment C, then A, then B

C is a correctness check and costs almost nothing. Do not report A or B before C
passes.

### 3.3 Decide the DINO-WM question

Experiment B needs a DINO-WM number. The published checkpoint
`kotmul/dinowm_patch_prop_pusht` now loads and runs after three fixes, all of
them scripted or configured rather than written down as steps to repeat
(`scripts/adapt_dinowm.py`, `scripts/plan/config/inzva_dinowm.yaml`).

**It has never been scored.** The run was cancelled for time. What we know is
what it costs: **about 4 hours per seed on a V100**, so roughly 12 GPU-hours for
three seeds, and the cluster GPU queue is currently quoting more than a day.

Three options, cheapest first:

1. Run the three seeds on TRUBA whenever the queue allows. If it scores near
   74%, Experiment B needs no training at all.
2. Drop Experiment B and report A and C only. A is the actual claim; B is
   generality evidence.
3. Train DINO-WM ourselves. Most expensive, and only justified if the
   checkpoint scores poorly and B is considered essential.

**Recommendation: do not let this block anything.** It is independent of the
critical path. Start it when the queue is free and carry on writing the method.

### 3.4 Still open

- Assign the six files to five people.
- Decide the seed count. Three is the floor, not a nicety: measured spread at
  50 episodes is 82% to 96%, so a single-seed number carries no information.
- A teammate should run the five commands in section 9 on their own machine.
  Done three times here, but never by someone who did not write the document.

---

## 4. Things that will bite you

Each of these cost hours to find. All are documented in full in the README.

- **Seed noise is 14 points.** At three seeds, any effect smaller than about 5
  points is indistinguishable from luck. Experiment A has to clear that bar, or
  show its gap widening consistently across budgets.
- **A frozen shared encoder may cap the coarse model.** It is trained for
  short-horizon prediction, and the coarse model needs features that predict 8
  steps ahead. If Experiment A shows no benefit at any budget while C passes,
  suspect this first (section 6.5).
- **TRUBA needs a non-default torch build.** The standard wheel has no kernels
  for its GPUs. Section 12.2.
- **DINO-WM is 145x slower than LeWM per plan.** Budget for it in days.
- **A refused `git pull` leaves a cluster running stale code.** Verify the pull
  landed before submitting. Section 7.x.

---

## 5. One-line summary

The instrument is built, calibrated and trusted on three machines; the
experiment it was built for has not been run, and the first line of the method
is still unwritten.
