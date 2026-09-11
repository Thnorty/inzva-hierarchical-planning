# inzva project setup

Hierarchical coarse-to-fine planning on PushT, built on the
[stable-worldmodel](https://github.com/galilai-group/stable-worldmodel) harness.

This file covers environment setup, data, and baseline reproduction. Experiment
configs and results live elsewhere in the repo.

---

## 0. Team rules (read before installing)

1. **Everyone installs the same commit.** Do not update it mid-project. The
   upstream repo is actively developed and recent commits have changed both the
   PushT success criteria and CEM itself, which would silently break comparisons
   between week 1 and week 3 numbers.

   ```text
   PINNED COMMIT: 6f1e499e9cc0c898d326112f485c1062c3d20f24
   ```

   Why this matters, concretely:

   | Commit | What it changed |
   |--------|-----------------|
   | `9d853d8` | PushT symmetric-shape success criterion |
   | `de031f0`, `73dade0` | PushT default block scale |
   | `15a8bb4` | CEM/iCEM elite variance → population std (`correction=0`). Reshuffles which episodes succeed by up to 10 points per seed, but moves the mean by 0.7 points (§6.1). Still pin it, since per-seed numbers are not comparable across it |

2. **Everyone installs the same dependencies.** A pinned commit pins our code
   and nothing underneath it. Upstream gitignores `uv.lock` because it ships a
   library; we track it, because an unbounded `transformers>=4.50.0` silently
   resolved to v5 and broke checkpoint loading for us (§7). Install with
   `uv sync`, which honours the lock, and never `uv lock --upgrade` without
   telling the team.

   Windows users still apply the CUDA torch swap by hand afterwards (§2.1). The
   lock cannot express a build variant.

3. **One shared eval config.** Nobody edits horizon, receding horizon, episode
   count, or seeds locally.

4. **Every reported number goes with the exact command that produced it.**
   `python scripts/collect_results.py` does this for you (§6.3).

---

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| git | any | |
| uv | latest | https://docs.astral.sh/uv/getting-started/installation/ |
| Python | 3.10 | uv installs it for you |
| CUDA GPU | optional locally | required for real eval runs. On Windows see §2.1 |
| zstd | any | to decompress the dataset. The venv's `zstandard` works too |
| Disk | ~60 GB free | 13 GB download + 46 GB decompressed. The Lance copy needs 13 GB total instead, see §5.2 |

Installing uv:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```powershell
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## 2. Clone and install

**Clone our repo, not upstream.** Upstream does not contain the shared config,
the verification scripts, or the loader patch without which the LeWM checkpoint
will not load at all (§7). The pinned upstream commit is already an ancestor of
our `main`, so there is nothing to check out by hand.

```bash
git clone https://github.com/Thnorty/inzva-hierarchical-planning
cd inzva-hierarchical-planning
uv venv --python=3.10
```

It is private, so ask for collaborator access first or the clone will 404.

Keep a link to upstream so you can see what changes there without pulling it in:

```bash
git remote add upstream https://github.com/galilai-group/stable-worldmodel
git fetch upstream          # look, do not merge
```

`origin` is our repo and `upstream` is theirs. Nobody merges `upstream/main`
without the whole team agreeing, for the reasons in §0.

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows (PowerShell)
.venv\Scripts\activate
```

```cmd
:: Windows (cmd.exe)
.venv\Scripts\activate.bat
```

Then install dependencies:


```bash
uv sync --extra all --group dev
```

`--extra all` pulls in both the environment and training dependencies. The base
install has neither, and the `data` extra alone only adds the Lance dataset stack.

### 2.1 Windows only: fix the CPU-only torch

`pyproject.toml` lists `torch` unversioned with no index configuration. On Linux
the default PyPI wheel bundles CUDA; **on Windows it does not**, so `uv sync`
installs `torch==2.11.0+cpu` and `torch.cuda.is_available()` is `False` no matter
what your GPU is doing. Swap in the CUDA build of the *same* versions:

```powershell
uv pip install --python .venv\Scripts\python.exe "https://download.pytorch.org/whl/cu128/torch-2.11.0%2Bcu128-cp310-cp310-win_amd64.whl" "https://download.pytorch.org/whl/cu128/torchvision-0.26.0%2Bcu128-cp310-cp310-win_amd64.whl"
```

This is a variant swap, not a version bump, so nothing else in the resolution
moves. **Any later `uv sync` reverts it** — re-run the command above afterwards.

`torchcodec` stays on its `+cpu` build. It imports and works fine against CUDA
torch (it is a decoder), but it is the first suspect if video-format dataset
loading throws.

---

## 3. Set STABLEWM_HOME

All datasets and model checkpoints are stored under `$STABLEWM_HOME`. It defaults
to `~/.stable_worldmodel/`, which we do **not** use.

**Point it at `.stable-wm/` inside the clone.** That directory is gitignored, so
the 46 GB dataset never appears in `git status` and a stray `git add .` cannot
try to stage it. Data and code stay together, so there is one path to quote when
someone asks where the dataset is.

```text
$STABLEWM_HOME = <clone>/.stable-wm
```

Upstream's `.gitignore` covers `checkpoints/` but not `datasets/`, which is why
we added the `.stable-wm/` line ourselves.

> Because the data lives inside the working tree, **never run `git clean -xdf`**
> in this clone. `-x` deletes ignored files, and 46 GB is a 13 GB re-download.
> Plain `git clean -df` is safe.

**macOS / Linux** (add to `~/.bashrc` or `~/.zshrc` so it persists):

```bash
export STABLEWM_HOME="$HOME/stable-worldmodel/.stable-wm"
```

**Windows PowerShell**, current session only:

```powershell
$env:STABLEWM_HOME = "C:\path\to\stable-worldmodel\.stable-wm"
```

**Windows PowerShell**, persistent (do this one, the line above is forgotten when
you close the terminal):

```powershell
[Environment]::SetEnvironmentVariable("STABLEWM_HOME", "C:\path\to\stable-worldmodel\.stable-wm", "User")
```

Reopen the terminal afterwards, then confirm:

```powershell
echo $env:STABLEWM_HOME
```

```bash
echo $STABLEWM_HOME
```

TRUBA is the one place to deviate: point it at a shared scratch path there so
five people do not download the same 13 GB five times.

---

## 4. Verify the install

```bash
swm envs                # should list swm/PushT-v1 under Continuous
swm fovs PushT-v1       # should print the factors of variation table
swm datasets            # empty on a fresh install, this is correct
swm checkpoints         # empty on a fresh install, this is correct
```

`swm datasets` and `swm checkpoints` list what is cached **locally**. An empty
result on a fresh machine means the install works and nothing has been downloaded
yet. It does not mean anything is missing.

A `pkg_resources is deprecated` warning from pygame is harmless. Ignore it.

Then check the GPU is actually reachable, not merely present:

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

You want a `+cuXXX` build and a real CUDA version, e.g.
`2.11.0+cu128 12.8 True`. Getting `2.11.0+cpu None False` means §2.1 has not been
applied — powering the GPU on does not change it, because the CPU wheel has no
CUDA compiled in at all.

---

## 5. The dataset

The eval protocol replays expert episodes, so `pusht_expert_train.h5` is required
even just to evaluate a pretrained checkpoint. It is **not** reachable through
`swm.data.load_dataset()`: the official copy is zstd-compressed, and
`stable_worldmodel/data/utils.py:143` only recognises `.h5`, `.hdf5` and `.lance`
on HuggingFace ("no tar/zst wrapping"). Fetch it by hand.

There is a **Lance copy of the same data** that needs no manual download and a
third of the disk. Read §5.2 before spending 46 GB on the HDF5 path, especially
on TRUBA.

| | |
|---|---|
| Source | `quentinll/lewm-pusht` (HF **dataset** repo) |
| File | `pusht_expert_train.h5.zst` |
| Download | 13.1 GB |
| Decompressed | **46.3 GB** |

**PowerShell (Windows)**:

```powershell
# 1. download (resumable — just re-run if it drops)
curl.exe -L -C - --create-dirs -o "$env:STABLEWM_HOME/datasets/pusht_expert_train.h5.zst" "https://huggingface.co/datasets/quentinll/lewm-pusht/resolve/main/pusht_expert_train.h5.zst"

# 2. decompress
zstd -d "$env:STABLEWM_HOME/datasets/pusht_expert_train.h5.zst" -o "$env:STABLEWM_HOME/datasets/pusht_expert_train.h5"
```

**Bash (Linux / macOS)**:

```bash
# 1. download (resumable — just re-run if it drops)
curl -L -C - --create-dirs -o "$STABLEWM_HOME/datasets/pusht_expert_train.h5.zst" "https://huggingface.co/datasets/quentinll/lewm-pusht/resolve/main/pusht_expert_train.h5.zst"

# 2. decompress
zstd -d "$STABLEWM_HOME/datasets/pusht_expert_train.h5.zst" -o "$STABLEWM_HOME/datasets/pusht_expert_train.h5"
```

In PowerShell remember to reference environment variables with `$env:STABLEWM_HOME` and use `curl.exe` (as bare `curl` is an alias for `Invoke-WebRequest`). If `zstd` is not on PATH, the
venv already ships the Python binding:

```bash
python -c "import zstandard, os, pathlib; d = pathlib.Path(os.environ['STABLEWM_HOME'])/'datasets'; fi = open(d/'pusht_expert_train.h5.zst','rb'); fo = open(d/'pusht_expert_train.h5','wb'); zstandard.ZstdDecompressor().copy_stream(fi, fo)"
```

Delete the `.zst` once `swm inspect pusht_expert_train.h5` reads it. Converting
to Lance (`swm convert`) shrinks it considerably, but `eval.dataset_name` has to
change with it — decide as a team, not unilaterally.

Training the DINO-WM baseline additionally needs the **video** format
(`prejepa.yaml` wants `pusht_expert_train_video`), another conversion off the
same source.

### 5.1 Provenance and verification

**Our copy is the right one, and this is settled.** Upstream's own conversion
script names it: `scripts/benchmark/convert.py:43` sets
`PUSHT_HF_REPO = 'quentinll/lewm-pusht'` and `PUSHT_HF_FILE =
'pusht_expert_train.h5.zst'`, and its docstring describes both PushT and
TwoRoom as "224x224 LeWorldModel sources". The Lance dataset that upstream's
README links as the benchmark source (§5.2) is the output of running that
script on this file. So this is not one of several plausible PushT datasets: it
is the input the harness authors convert from.

| | |
|---|---|
| Source of record | `quentinll/lewm-pusht` (HF **dataset** repo) |
| Named by | `scripts/benchmark/convert.py:43-44` |
| File | `pusht_expert_train.h5.zst` -> `pusht_expert_train.h5` |
| Size on disk | 46,300,921,856 bytes (43.1 GiB) |
| Episodes | 18,685 |
| Steps | 2,336,736 |
| Episode length | 49 to 246, mean 125.1 |
| HDF5 keys | `action`, `pixels`, `proprio`, `state`, `episode_idx`, `step_idx`, `ep_len`, `ep_offset` |
| Reader | `HDF5Dataset`, via `swm.data.load_dataset()` on the local path |

The file carries no HDF5 attributes, so there is no embedded provenance to
check. The counts above are the fingerprint. Anything that differs is a
different dataset.

Checks that passed, all through the repo's own dataset API:

- **`state` and `pixels` are aligned.** Projecting `state[:2]` from the 512-unit
  window into the 224 px render (scale 0.4375) lands on the rendered agent to
  within **0.73 px mean, 1.09 px max** over 13 frames of episode 0. The same
  holds for the block at `state[2:4]`.
- **Actions drive the state.** `corr(action_x, delta_agent_x) = 0.995` and
  `corr(action_y, delta_agent_y) = 0.992` within an episode. Actions are
  relative targets: `step()` sets `target = agent_pos + action * 100` and
  PD-controls toward it, so one step covers roughly 40% of the commanded delta
  rather than all of it. That is the controller, not a bug.
- **`proprio` is exactly `[state[:2], state[-2:]]`**, max absolute difference
  `0.0`. It carries no independent information.

One thing that will bite if you assume otherwise:

- **`pixels` changes layout when you read it.** On disk it is
  `(2336736, 224, 224, 3)`, plain HWC. The reader permutes it to CHW at
  `stable_worldmodel/data/formats/hdf5.py:130`, so `load_episode()` hands you
  `(T, 3, 224, 224)`. Torch wants that; PIL, imageio and matplotlib do not, and
  need `transpose(0, 2, 3, 1)` back. The failure is loud (`Cannot handle this
  data type`) but the cause is not. If you open the file directly with `h5py`
  you get HWC and no permute happens at all.

Reproduce all of the above with:

```bash
python scripts/verify_dataset.py
```

### 5.2 There is a Lance copy, and its pixels are lossy

The handoff asked whether `galilai-group/lewm-pusht` — same org as the harness,
published later — is the canonical copy. It exists, and it is **not** a
duplicate. It is the same data in a different format.

| | `quentinll/lewm-pusht` | `galilai-group/lewm-pusht` |
|---|---|---|
| Format | HDF5, zstd-compressed | Lance |
| Files | `pusht_expert_train.h5.zst` | `pusht_expert_train.lance/` |
| Download | 13.1 GB | 13.3 GB |
| On disk after setup | **46.3 GB** | **13.3 GB** |
| Manual steps | curl, then zstd decompress | none |
| Last modified | 2026-03-27 | 2026-05-13 |
| Downloads / likes | 1918 / 12 | 539 / 0 |
| README says | "Official dataset" | "**Lance version of the official dataset**" |

Its own README states it is a re-encoding of the same LeWorldModel dataset, and
its Lance manifest carries the identical schema: `episode_idx int32`,
`step_idx int32`, `action float[2]`, `proprio float[4]`, `state float[7]`,
`pixels binary`.

`quentinll/lewm-pusht` stays the **source of record** — it is the original, and
the numbers in §5.1 were measured on it. But the Lance copy is the better thing
to put on the cluster:

- **33 GB less disk**, which matters when five people share a scratch quota.
- **No manual download.** `.lance` is one of the three suffixes
  `data/utils.py` recognises on HuggingFace, so
  `swm.data.load_dataset('galilai-group/lewm-pusht')` fetches and caches it
  directly. No curl, no zstd, no 46 GB intermediate.
- It is the format `swm convert` would produce anyway, already produced by the
  people who maintain the harness.

**We downloaded it and checked. Here is exactly what it is.**

Identical where it matters for evaluation:

- Same 2,336,736 rows in the **same order** as the HDF5.
- `action`, `proprio` and `state` are **bit-identical**.
- The eval's episode sampling selects the same 50 episodes at seeds 0, 1, 2
  and 42, from the same 1,869,611 valid starting points.

Different in one way that matters for training:

- **`pixels` is lossy JPEG.** That is where the 33 GB goes. Decoded frames
  differ from the HDF5 by up to 19 intensity levels per channel, mean about
  0.1. The HDF5 stores raw `uint8` behind an HDF5 compression filter, which is
  lossless.

So the decision splits by use:

| Use | Verdict |
|-----|---------|
| **Evaluation** | Either format. The eval caches only `action`, `proprio` and `state` and renders goal frames from the env; it never reads dataset pixels |
| **Training a world model** | **HDF5.** Pixels are the model input, and training a visual encoder on JPEG artifacts to evaluate on cleanly rendered frames introduces a train/test mismatch for no scientific reason |

Since our GRU trains on pixels, the 33 GB saving is not available to us where it
would have counted. **Decision: we use the HDF5 and do not keep a Lance copy.**
The one we downloaded for the comparison above has been deleted; it is
re-fetchable in one command if anyone later needs an eval-only copy.

```bash
python -c "import stable_worldmodel as swm; swm.data.load_dataset('galilai-group/lewm-pusht')"
```

Note that loading it through the repo reader needed more memory than this laptop
had spare, and was killed. The comparison in this section was done by reading the
Lance fragments directly with `lance.dataset(...)` and pulling single columns,
which is cheap. Worth knowing before someone points `eval.dataset_name` at it.

If you do adopt it for something, `eval.dataset_name` has to change to match, and
that is a shared-config edit rather than a unilateral one.

### 5.3 Actions leave the declared action space, and that is fine

`PushT-v1` declares `Box(-1, 1, shape=(2,))`, and the expert data does not
respect it. Measured over all 2,336,736 steps, not a sample:

| | x | y |
|---|---|---|
| min | -1.495 | -1.466 |
| max | **2.043** | **1.792** |
| std | 0.208 | 0.207 |

2,904 of 2,336,736 steps sit outside the box, which is **0.124%**.

It looks alarming and it changes nothing. Three measurements say so.

**Nothing clips, anywhere along the path.** `CEMSolver` stores the action space
but only reads `.shape` from it; there is no `clip` or `clamp` in
`planning/solver/cem.py`. `BasePolicy` inverse-transforms the plan and returns
it (`policy.py:537`). `PushT.step()` has its clip line commented out
(`envs/pusht/env.py:326`). So the environment executes whatever is proposed,
in-box or not, and always has.

**The scaler barely moves.** `eval_wm.py` fits a `StandardScaler` on the action
column. Fitting it on raw data versus data clipped to the box:

| | mean shift | std shift |
|---|---|---|
| x | 1.3e-4 | 0.45% |
| y | 9.2e-6 | 0.13% |

A 0.45% change in a normalisation constant is not a source of anything.

**The solver never goes near the boundary.** Because the action std is 0.208,
the box edge sits at **±4.8 sigma** in normalised units. CEM draws `N(0, 1)`
there (`var_scale: 1.0`), so the fraction of samples reaching ±1 in raw units
rounds to zero. The solver is not being clipped, and it is not straining
against a wall either.

**Decision: do not clip. Anywhere.** Not the training data, not the solver
output.

- Clipping training targets would distort 0.124% of steps to model a boundary
  the environment does not enforce.
- Clipping solver output would add a constraint CEM never reaches, which costs
  compute and buys nothing.
- Clipping one but not the other creates a train/execute mismatch, which is the
  only way this becomes a real bug.

This applies to `models/gru_wm.py`, `models/gru_coarse.py` and
`solver/hierarchical.py` when they are written. Fit scalers on raw actions, the
same way `eval_wm.py` does, so the GRU baseline and the reference share one
normalisation.

---

## 6. Baselines: what exists and what does not

From the stable-worldmodel baselines page, Push-T success rates:

| Model | Success rate | Official checkpoint published? |
|-------|--------------|-------------------------------|
| DINO-WM | 74% | **No** |
| PLDM | 78% | No |
| LeWM | 96% | **Yes** — `quentinll/lewm-pusht` |
| GCBC | 75% | No |

**Important:** those numbers use a fixed 50 step budget, not the unlimited budget
used in the original DINO-WM paper. Our eval config must match the 50 step budget
or the comparison is meaningless.

Every `Checkpoint` cell in the upstream docs table reads `NA`. Searching HF for a
released DINO-WM checkpoint in the layout `load_pretrained()` expects
(`config.json` + `weights.pt`) turns up only these:

| Repo | What it is | Verdict |
|------|-----------|---------|
| `quentinll/lewm-pusht` | Official LeWM checkpoint, correct layout | **Use this** |
| `kotmul/dinowm_patch_prop_pusht` | Community PreJEPA, epoch 10, ~11 downloads, no published number | Smoke test only |
| `kevin510/swm-dino-wm-checkpoints` | Raw hydra run dirs, wrong layout, 0 downloads | Ignore |

### Consequence for week 1

**Reproduce LeWM at 96%, not DINO-WM at 74%.** It is the only official
checkpoint, and it validates the eval config, the dataset and the solver exactly
as well as DINO-WM would — in a day rather than a training run.

DINO-WM stays the Experiment B comparison baseline, but obtaining it means
**training it ourselves**. In this repo "DINO-WM" is PreJEPA with a frozen
`dinov2_small` backbone: `scripts/train/prejepa.py`, config
`scripts/train/config/prejepa.yaml`. Budget for that in the week 1 plan.

---

## 6.1 The shared eval config

`scripts/plan/config/inzva_pusht.yaml`. It inherits upstream's `pusht.yaml` and
locks the five things that have to be identical across people and runs: horizon,
receding horizon, action block, eval budget, and episode count. It also sets
`history_len: 3` in the file, so the `+` prefix and the silent fallback to `1`
both stop being possible.

**Nobody edits it alone.** Overriding any of those on the command line produces
a number that is not comparable to anyone else's, which is the whole failure
this file exists to prevent.

| Key | Value | Why |
|-----|-------|-----|
| `plan_config.horizon` | 5 | `horizon * action_block <= eval_budget` is asserted |
| `plan_config.receding_horizon` | 5 | replan every 5 blocks |
| `plan_config.action_block` | 5 | fixed by the checkpoints' `in_chans: 10` |
| `plan_config.history_len` | 3 | matches the LeWM predictor's `num_frames: 3` |
| `eval.eval_budget` | 50 | the budget the published table uses |
| `eval.num_eval` | 50 | episodes per run |
| `seed` | 42 | swept to `0,1,2` for anything reportable |

Run it:

```bash
python scripts/plan/eval_wm.py --config-name inzva_pusht policy=quentinll/lewm-pusht
```

Three seeds, which is the floor for a reported number:

```bash
python scripts/plan/eval_wm.py --config-name inzva_pusht -m \
    policy=quentinll/lewm-pusht seed=0,1,2
```

Check what a run will actually use before spending GPU hours on it:

```bash
python scripts/plan/eval_wm.py --config-name inzva_pusht --cfg job
```

## 6.1b Reproduction: closed

**Verdict: we could not reproduce 96%, and we stopped looking. Our baseline of
record is 87.5%, and every mechanical explanation for the difference has been
tested and eliminated.** This section is the whole investigation, so nobody
repeats it.

Per the standing rules, "hierarchy did not help" is a valid finding and a number
we cannot reproduce is not. The same applies here: this is a closed question
with a documented answer, not an open task.

### The baseline of record

```bash
python scripts/plan/eval_wm.py --config-name inzva_pusht -m \
    policy=quentinll/lewm-pusht seed=0,1,2
python scripts/collect_results.py
```

| Seed | Success |
|------|---------|
| 0 | 42/50 = 84% |
| 1 | 48/50 = 96% |
| 2 | 41/50 = 82% |
| 42 | 44/50 = 88% |

| | |
|---|---|
| Mean over seeds 0, 1, 2 | **87.3%**, std 7.6 |
| All four seeds | 87.5%, std 6.2 |
| Pooled | 175/200 = 87.5%, 95% CI [82.2%, 91.4%] |
| Published | 96% |

Full records with versions attached: `notes/results/inzva_pusht_results.md`.

Quote it as **87.3% ± 7.6 over three seeds**, with the command. Never quote 96%
as ours.

### The target, recovered from git rather than asked about

`docs/baselines.md` states only a fixed 50-step budget: no episode count, no seed
count, no statement of whether 96% is a mean. But the commit that added the row,
`44c45bd` ("Adding LeWM", 2026-03-23), edited `scripts/plan/config/pusht.yaml`
in the same change. That file at that commit is the protocol.

Every numeric planning parameter matches ours: `num_eval` 50, `eval_budget` 50,
`goal_offset_steps` 25, `img_size` 224, `horizon` 5, `receding_horizon` 5,
`action_block` 5, and CEM at `num_samples` 300, `n_steps` 30, `topk` 30,
`var_scale` 1.0.

Two things differ, and neither is tuning: it used the old `world.history_size: 1`
API in place of `plan_config.history_len`, and it read the Lance dataset rather
than HDF5.

**Its `seed` is 42, and nothing in that commit runs a sweep.** Combined with our
measured range of 82% to 96%, the most economical explanation is that the
published figure is a single seed that landed high. Our own seed 1 hit 96%
exactly. If that is what happened, there is nothing to converge to.

### Every mechanical explanation, tested and eliminated

| Candidate | Verdict | Evidence |
|-----------|---------|----------|
| `15a8bb4`, CEM elite variance | **Not the cause** | Reverted the line, reran 3 seeds. +0.7 points; paired over 150 episodes, 6 fail→pass against 5 pass→fail; exact McNemar p = 1.00 |
| `9d853d8`, success criterion | **Cannot fire** | It compares angles modulo a shape's symmetry, but the table covers only square, +, I and Z. Our block is `T`, so symmetry stays 2π. `_get_obs` already wraps the angle (`env.py:381`) and the dataset confirms `state[4]` spans 0 to 6.2832 |
| `de031f0` + `73dade0`, block scale | **Cancel** | The first deleted a hardcoded `scale = 30` so the variation value (40) applied; the second set that value to 30. Effective scale is 30 before and after |
| Env geometry generally | **Unchanged** | Setting the env to a recorded state reproduces the recorded frame: mean absolute difference under 0.5 of 255, about 0.3% of pixels differing, all edge antialiasing. `scripts/check_env_matches_dataset.py`. Read its pass/fail rather than the percentage, which shifts slightly between checkouts because SDL picks rendering paths at runtime |
| Protocol parameters | **Identical** | Recovered from `44c45bd`; see above |
| Dataset format, HDF5 vs Lance | **Irrelevant** | Downloaded the Lance copy and compared directly. Same row count and same row *order*; same 1,869,611 valid starting points; identical episode selection at seeds 0, 1, 2 and 42; `action`, `proprio` and `state` bit-identical. Its pixels are lossy JPEG (§5.2) but the eval never reads dataset pixels |

That last row is why we did not bother running the eval on Lance: it would
replay the same 50 episodes from bit-identical states.

### What actually explains the spread

Two sources, both measured, neither fixable by configuration.

- **Seed variance.** 82% to 96% across four seeds at 50 episodes.
- **Run-to-run nondeterminism.** Rerunning seed 0 unchanged gave 43/50 against
  the original 42/50 (§6.4). About two points, from CUDA kernel nondeterminism
  amplified by CEM reordering near-tied candidates.

The CEM ablation showed the same thing from another angle: a 1.7% change in one
solver constant moved individual seeds by up to 10 points while leaving the mean
flat. **Per-seed numbers on PushT carry almost no information.** Three seeds is
the floor, and report the spread.

### Why this is fine for the actual project

Experiment A compares our coarse-to-fine solver against our own GRU + CEM
baseline on this stack. Both sides carry the same offset from the published
figure, so it cancels out of the comparison the project is actually about. The
reproduction mattered because it is how we learned the offset is a constant
property of this stack rather than a symptom of something misconfigured that
would also distort A. We now know which.

What we cannot do is claim to have reproduced DINO-WM or LeWM at published
numbers. We did not. Say so.

---|
| Pipeline smoke | 4 | 50 samples, 10 steps | 25% | not reportable |
| Reduced | 10 | stock (300, 30) | **90%** | 96% |

Nine of ten at the stock solver settings is consistent with the published 96%:
the 95% interval on 9/10 runs from roughly 56% to 100%. It confirms the dataset,
the eval protocol, the checkpoint and the solver are wired up correctly. It is
**not** the reproduction — that needs the full 50 episodes and three seeds, on
TRUBA.

## 6.2 Train/validation split

The HuggingFace repo ships one file and no validation split, so we define our
own. `scripts/inzva_split.py`.

**Split at episode granularity, never step granularity.** Consecutive steps of
one PushT episode are near-duplicates. A step-level split puts frame `t` in
train and frame `t+1` in validation, and validation loss then measures memory
rather than generalization. It looks great and means nothing.

The split is a rule rather than a stored list. Same episode count, same seed,
same fraction gives the same held-out episodes on every machine:

| Parameter | Value |
|-----------|-------|
| `SPLIT_SEED` | `20260910` |
| `VAL_FRACTION` | `0.05` |
| Train episodes | 17,751 |
| Val episodes | 934 |
| Fingerprint | `2d5f8c4f85e918f8` |

Use it from a training script:

```python
from scripts.inzva_split import split_episodes

train_eps, val_eps = split_episodes(num_episodes=18685)
```

Before comparing your loss curve to anyone else's, compare fingerprints. It
takes a second and it catches the failure that otherwise costs a week:

```bash
python scripts/inzva_split.py --fingerprint-only
# 2d5f8c4f85e918f8
```

A different fingerprint means a different held-out set, which means the two
curves were never comparable. If the episode count is not 18,685 the script
warns, because that means the dataset is not the one the split was designed
against.

Changing the seed or the fraction invalidates every loss curve and checkpoint
comparison made before the change. Do not do it quietly.

## 6.3 Where results are saved

`eval_wm.py` appends the full config and the per-episode outcomes to
`$STABLEWM_HOME/checkpoints/<owner>/<output.filename>` after every run. That is
the ground truth and it already has everything worth keeping.

The problem is where it lives. `$STABLEWM_HOME` is `.stable-wm/`, which is
gitignored, so those results are one `git clean -xdf` or one fresh clone from
gone, and nobody else on the team can see them. Hydra's `outputs/` and
`multirun/` directories are gitignored upstream too, so they do not help.

`scripts/collect_results.py` reads those files and writes a tracked summary
into `notes/results/`, one Markdown table for people and one JSON for scripts:

```bash
python scripts/collect_results.py                                  # shared config runs
python scripts/collect_results.py --results-file pusht_results.txt # upstream config runs
```

It records the commit SHA, torch, CUDA, GPU and **transformers version**
alongside every number. That last one is not padding: a transformers major
version is what broke checkpoint loading (§7), and a results file that does not
name it cannot be debugged later.

Run it after any eval you care about. The per-episode boolean arrays stay in the
source file under `$STABLEWM_HOME`; if you need those, copy the file out before
cleaning anything.

One trap worth knowing, because it cost us a silent failure: upstream's
`.gitignore` has a bare `results/` line, and a pattern without a leading slash
matches a directory of that name **at any depth**. So `notes/results/` was
ignored too, and the tracked record was not tracked at all. We re-include it
explicitly at the bottom of `.gitignore`. If you add another results directory
anywhere in this tree, check it with `git check-ignore -v <path>` before
assuming it is committed.

## 6.4 Will a second machine get the same number?

Pinning dependencies is necessary. It is not sufficient. Both halves matter and
they fail in different ways.

### What pinning fixes, and it is now done

`uv.lock` was gitignored upstream, which is correct for a library and wrong for
us. Five people running `uv sync` on five days resolved five dependency sets,
and an unbounded `transformers>=4.50.0` is exactly how v5 arrived and broke
checkpoint loading (§7). **The lock is now tracked.** It pins
`transformers==5.16.1` and `torch==2.11.0` explicitly, so that class of failure
is closed.

One caveat that the lock cannot cover: on Windows the CUDA torch wheel is
installed out of band (§2.1), so the lock records `torch 2.11.0` while the venv
actually holds `2.11.0+cu128`. The build variant is a manual step and stays a
manual step. `scripts/collect_results.py` records the *installed* version, not
the locked one, which is why its environment table is the thing to compare.

### What pinning does not fix

Identical packages do not imply identical floating-point results on different
hardware. cuBLAS and cuDNN select kernels by GPU architecture, and different
kernels reduce in different orders, so the last bits of a matmul differ between,
say, an RTX 3060 and an A100. TF32 behaviour differs across generations too.

Normally that is noise below anything you would notice. **CEM amplifies it.**
The solver ranks 300 candidates by cost and keeps the top 30. When two
candidates are nearly tied, a difference in the last bits flips their order,
which changes the elite set, which changes the next sampling distribution, and
that compounds across 30 iterations. An episode whose outcome was marginal then
lands on the other side. At 50 episodes, one flipped episode is two percentage
points.

Sampling itself is not the problem: `torch.randn` with a seeded generator is
counter-based and gives the same stream for the same shape. The divergence comes
from the ViT forward pass and the cost evaluation.

### What to expect, and what to check

**Measured, not assumed.** A fresh clone of this repo into a different directory
on the same machine, installed from scratch by following §2, reproduces the
original almost exactly:

| Seed | Original | Fresh clone | Episodes differing |
|------|----------|-------------|--------------------|
| 0 | 42/50 | 42/50 | 0 |
| 1 | 48/50 | 47/50 | 1 |
| 2 | 41/50 | 42/50 | 1 |

| | |
|---|---|
| Original mean | 87.3% |
| Clone mean | **87.3%** |
| Episodes differing | 2 of 150 |

Across every paired run we have done on this machine, **3 episodes in 200
disagree, about 1.5%**. In practice that means a rerun usually matches exactly
and occasionally moves by a single episode, which is 2 points on a 50-episode
rate. It is not a constant 2-point tax.

The cause is ordinary CUDA nondeterminism: cuDNN autotuning picks algorithms per
run and some reductions use atomics whose accumulation order is not fixed.
Normally invisible; here CEM amplifies it, because a last-bit cost difference
reorders near-tied candidates and the rollout diverges from there. Only episodes
that were already marginal flip.

So per-seed rates are *nearly* reproducible and the three-seed mean is solidly
so. The sensible acceptance test is still the **mean over three seeds**, because
that is robust to the occasional flipped episode without needing anyone to argue
about which one flipped.

| Comparison | Expect |
|---|---|
| Same machine, rerun or fresh clone | Same mean. Zero or one episode different per seed |
| Different machine, same GPU model | Same, as far as we can tell. Untested, and we have no second machine to test it on |
| Different GPU model | Means should agree within seed noise; per-seed rates drift further |

When two people disagree by more than a couple of episodes per seed, compare the
environment table in `notes/results/*.md` before suspecting anything else. That
table exists for this.

### We are not chasing bit-exact determinism

PyTorch can be forced onto deterministic kernels
(`torch.use_deterministic_algorithms(True)`, `cudnn.deterministic`,
`CUBLAS_WORKSPACE_CONFIG`), which would make a rerun bit-identical. **We are not
doing this.** It costs speed, it raises outright if any op lacks a deterministic
kernel, and the claim we are testing does not need that resolution: Experiment A
asks whether two-timescale planning beats one-timescale planning by more than
seed noise, and seed noise is already an order of magnitude larger than
run-to-run jitter.

Two points of rerun noise is simply part of the measurement. Report means over
three seeds with the spread, and it is accounted for.

---

## 7. Known gotchas

- **The published LeWM checkpoint does not load on a fresh install.** This is the
  one that will stop you dead, so it is first. `pyproject.toml` asks for
  `transformers>=4.50.0` with no upper bound, so `uv sync` today installs
  **transformers 5.x**. HuggingFace renamed the ViT submodules in v5:
  `encoder.layer` became `layers`, the `ViTSelfAttention`/`ViTSelfOutput` pair
  collapsed into one `attention` with `q_proj`/`k_proj`/`v_proj`/`o_proj`, and
  `intermediate`/`output` became `mlp.fc1`/`mlp.fc2`. `quentinll/lewm-pusht` was
  saved under v4, so `load_pretrained` dies with ~300 missing and ~300
  unexpected keys.

  The weights are fine. All 303 tensors match by shape once the keys are
  renamed, so this is cosmetic damage, not a broken checkpoint. v5 does ship a
  converter (`WeightConverter`), but it only runs inside `from_pretrained`, and
  `load_pretrained` restores a raw `state_dict` with `load_state_dict`, which
  bypasses it.

  **We patched `stable_worldmodel/wm/utils.py`** to retry the load through a
  key-rename table when the strict load raises. It is version-agnostic, so it
  works whether you are on transformers 4 or 5, and it survives `uv sync`
  because it is repo code rather than a pinned dependency. You will see this
  line on a successful load, and it is expected:

  ```text
  quentinll/lewm-pusht: loaded after renaming pre-v5 transformers ViT keys.
  ```

  Upstream has not fixed this as of `4821c8e`, one commit past our pin. Worth a
  PR if someone has a spare hour.

- **`uv.lock` is gitignored upstream, so "same commit" is not "same install".**
  This is what let the problem above happen at all: `.gitignore:232` excludes
  `uv.lock`, so five people running `uv sync` on five days get five dependency
  sets. Pinning the commit pins our code, not the ~200 packages under it. If a
  number moves and nobody touched the code, diff `uv pip freeze` before
  suspecting anything else.

- **`plan_config.history_len` needs a `+`, and the docs get this wrong.**
  `history_len` is commented out in `scripts/plan/config/pusht.yaml`, so it is
  absent from the composed config and Hydra refuses to override a key that is
  not there:

  ```text
  Could not override 'plan_config.history_len'.
  To append to your config use +plan_config.history_len=3
  ```

  Use `+plan_config.history_len=3`. Better: uncomment it in the shared config so
  nobody has to remember, because the failure mode when you forget is not an
  error. It defaults to `1`, the LeWM predictor has `num_frames: 3`, and you get
  a quietly bad number.

- **`action_block=5` is not free to change.** The published checkpoints encode
  actions with `in_chans: 10` = 2 action dims × frameskip 5, so changing the
  block size breaks the action encoder's input dimension. This also means the
  stock baseline *already plans at a 5-env-step time scale* — which matters for
  how the spec frames the hierarchy claim.
- **Plan length is asserted, not advisory.** `scripts/plan/eval_wm.py:69`
  requires `horizon * action_block <= eval_budget`. With the stock config that is
  5 × 5 = 25 ≤ 50. Experiment A's sweep has to stay inside it.
- **Factor count: 17 total, 14 usable.** `swm fovs PushT-v1` prints 17. Three
  (`agent.start_position`, `block.start_position`, `block.angle`) are randomized
  at every reset by default, so they are not a distribution shift at all —
  `scripts/data/collect_pusht_fov.py` excludes them, leaving 14. The spec says
  16; it is wrong and should say 14.
- **6 GB of VRAM cannot run the stock eval config**, at any batch size. One frame
  of PreJEPA latents is 256 patches × 404 dims × 4 B ≈ 414 KB *per candidate*,
  and the shipped config's 50 envs × 300 samples = 15,000 candidates ≈ 6.2 GB for
  a single frame, before activations. Laptop smoke tests: `eval.num_eval=4
  solver.num_samples=50 solver.n_steps=10`. Those prove the pipeline; they are
  not numbers anyone may report.
- **Spaces in the project path.** Most things cope, but Hydra config overrides and
  shell scripts sometimes do not. First suspect for any strange parse error.
- **Session-only env vars on Windows.** See section 3. Use the persistent form.
- **`uv sync` reverts the CUDA torch on Windows.** See section 2.1.

---

## 8. Status

Done:

- [x] Repo cloned, venv created, `uv sync` completed
- [x] `STABLEWM_HOME` set, persistent, inside the clone at `.stable-wm/` (§3)
- [x] `swm envs` and `swm fovs` verified
- [x] Commit SHA pinned and written into this file
- [x] CUDA torch verified on at least one machine (`2.11.0+cu128`, RTX 3060)
- [x] PushT expert dataset downloaded, decompressed, and **verified** (§5.1)
- [x] Dataset provenance recorded, and the `galilai-group` Lance copy identified (§5.2)
- [x] LeWM checkpoint loads — needed the transformers v5 loader patch (§7)
- [x] Planning pipeline runs end to end; four seeds average 87.5% (§6.1)
- [x] Action-space question resolved: do not clip, anywhere (§5.3)
- [x] Dataset confirmed as upstream's own source of record (§5.1)
- [x] Shared eval config written: `scripts/plan/config/inzva_pusht.yaml` (§6.1)
- [x] Train/val split defined and deterministic (§6.2)
- [x] Eval results saved to a tracked location, with versions (§6.3)
- [x] `uv.lock` tracked, so dependencies are pinned as well as the commit (§0)
- [x] `15a8bb4` tested as the cause of the gap and ruled out (§6.1)
- [x] Published protocol recovered from git; identical to ours except dataset
      format and the old history API (§6.1)
- [x] Success criterion, block scale and env geometry all ruled out (§6.1)
- [x] Run-to-run determinism measured: the eval is **not** reproducible
      bit-for-bit even on one machine (§6.4)
- [x] Lance copy downloaded and compared: same row order, bit-identical
      `action`/`proprio`/`state`, identical episode selection, lossy JPEG
      pixels (§5.2)
- [x] Clone test run here: fresh clone reproduces 87.3%, and fixed two bugs
      it exposed in the install instructions (§9)
- [x] `.gitattributes` added; a Windows checkout is now pure LF, so Linux and
      macOS teammates see no phantom diffs
- [x] Pushed to `Thnorty/inzva-hierarchical-planning` (private)
- [x] **Reproduction closed** (§6.1b). 96% not reproducible; every mechanical
      explanation tested and eliminated; baseline of record is 87.3% ± 7.6

Open, in the order they block things:

- [ ] A **teammate** runs the five commands in §9. We already ran them in a
      fresh clone here, which matched to the decimal and caught two real bugs
      (§9); what that could not change is the machine. Half an hour.
- [ ] **Image resolution decided.** Pixels are stored at 224×224 because that is
      DINO's input size. The GRU almost certainly does not need it, and 64×64 is
      roughly 12× the throughput. It affects both the coarse and the fine model,
      so it goes in the shared config and is decided once. Nobody has measured
      the accuracy cost yet — that measurement is the decision.
- [ ] **Six files assigned to five people** (`models/gru_wm.py`,
      `models/gru_coarse.py`, `solver/hierarchical.py`, `scripts/train_gru.py`,
      `scripts/sweep.py`, `README.md`)
- [ ] **`k` chosen** (start at 4), whether coarse and fine share an encoder
      (probably yes), and how many seeds the compute allows (3 is the floor)
- [ ] Decide whether TRUBA uses the Lance copy, and verify its counts first (§5.2)
- [ ] Experiment C (`k = 1`) scores like the GRU + CEM baseline — run this
      before A and B
- [ ] DINO-WM trained (`scripts/train/prejepa.py`) and its number recorded

Two things worth deciding early because they are cheap now and expensive later:

- **Three seeds is a floor, not a nicety** (§6.1). Measured spread on PushT at
  50 episodes is 82% to 96%. A single-seed number here carries no information.

---

## 9. What we added to the repo

Everything below is ours. The rest of the tree is upstream at `6f1e499`.

| Path | What it does | Section |
|------|--------------|---------|
| `INZVA_README.md` | This file | — |
| `scripts/plan/config/inzva_pusht.yaml` | The shared eval config. Inherits upstream's `pusht.yaml`, locks our protocol | §6.1 |
| `scripts/verify_dataset.py` | Confirms the dataset is the one we think it is: counts, alignment, action range | §5.1 |
| `scripts/check_env_matches_dataset.py` | Confirms the env still matches the one that generated the data | §6.1 |
| `scripts/inzva_split.py` | Deterministic episode-level train/val split, with a fingerprint | §6.2 |
| `scripts/collect_results.py` | Turns eval output into a tracked record with versions attached | §6.3 |
| `notes/results/` | The tracked records themselves | §6.3 |

Two upstream files carry local edits, both deliberate and both documented:

| Path | Edit | Why |
|------|------|-----|
| `stable_worldmodel/wm/utils.py` | `load_pretrained` retries through a key-rename table | The published LeWM checkpoint does not load under transformers v5 (§7) |
| `.gitignore` | Adds `.stable-wm/`, re-includes `notes/results/` and `uv.lock` | Keeps 46 GB out of git while keeping our records *in* it (§6.3) |

### Checking a fresh machine

Run these on a clean clone before trusting anything it produces:

```bash
python scripts/verify_dataset.py
python scripts/check_env_matches_dataset.py
python scripts/inzva_split.py --fingerprint-only
python scripts/plan/eval_wm.py --config-name inzva_pusht -m \
    policy=quentinll/lewm-pusht seed=0,1,2
python scripts/collect_results.py
```

Expected: 18,685 episodes, a passing env check, fingerprint
`2d5f8c4f85e918f8`, and a three-seed mean near 87%.

**This is not a hardware test.** We already know two machines cannot agree
exactly, because one machine cannot even agree with itself: rerunning a seed
unchanged moved it by an episode (§6.4). Everyone on this project runs the same
GPU anyway, so hardware variation is not the interesting variable.

What it actually catches is **a broken setup, and a wrong document**. The install
has real landmines, and each one fails loudly rather than subtly:

| If this went wrong | You will see |
|---|---|
| CUDA torch reverted by `uv sync` (§2.1) | CPU-only run, minutes per plan, or an outright failure |
| Loader patch missing (§7) | ~300 missing keys, the checkpoint never loads |
| `history_len` not applied (§7) | A quietly bad number, far below 87% |
| Wrong or partial dataset | Episode count is not 18,685 |
| Different env version | The env check fails outright |
| Different split parameters | The fingerprint differs |

So read the outcome coarsely. A three-seed mean anywhere near 87% with a wide
per-seed spread means the setup is right. A number nowhere near it means
something in the list above is wrong, and the environment table in
`notes/results/inzva_pusht_results.md` says which.

The second reason is less obvious and matters more: **nobody has followed this
document on a clean machine.** It was written from a session where everything
was already working, which is exactly how setup instructions acquire silent
gaps. The run is as much a test of §2 and §3 as of the person's laptop.

### This was run once, and it found something

A fresh clone into a different directory on the same machine, installed by
following §2 and §2.1 from scratch, then run through all five commands.

What it confirmed:

| Check | Result |
|-------|--------|
| Line endings on a Windows checkout | 292 files LF, **0 CRLF**, clean `git status` |
| `uv sync` honours the lock | Lockfile unchanged; `transformers` stayed pinned at 5.16.1 |
| Environment reproduces | 227 packages in both, identical except the project's own editable path |
| Dataset checks | 18,685 episodes, same correlations, same 2,904 out-of-box actions, same alignment |
| Split fingerprint | `2d5f8c4f85e918f8`, matching |
| Three-seed mean | **87.3%**, matching the original to the decimal; 2 of 150 episodes differed |

What it found, which is the point of doing it:

- **§2 told people to clone upstream.** Following the README exactly gave you
  none of the shared config, none of the scripts, and not the loader patch,
  so the checkpoint would fail with ~300 missing keys and no explanation.
  Fixed in `7ea1425`.
- **The CPU-torch trap is real and still bites.** `uv sync` installed
  `2.11.0+cpu` exactly as §2.1 warns. The lock pins the version, not the build
  variant, so that step cannot be automated away.
- **The env check's percentage is not bit-stable** between checkouts, even with
  identical sources and packages. Read its pass/fail, not its number.

Worth repeating on a teammate's machine, since that is the one variable this
run could not change.

