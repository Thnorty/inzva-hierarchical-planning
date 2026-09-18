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

The repo is **public**, so cloning needs no authentication and no collaborator
access. Read-only clone works for anyone, including inside WSL, where Windows
credentials do not carry over anyway.

You still need credentials to **push**. Set that up once per machine:

```bash
# GitHub CLI, easiest if you already use it
gh auth login
```

**Being public has one consequence worth knowing: everything here is visible,
including the results records and the reproduction write-up.** Nothing in the
repo is sensitive (no credentials, no absolute paths, no personal data; the only
machine detail is the GPU model, which is deliberate provenance for the numbers).
But treat anything you commit from now on as published.

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

### 2.0b If `box2d-py` fails to build

```text
error: command 'swig' failed: No such file or directory
```

`gymnasium[all]` pulls in `box2d-py`, which has no wheel and compiles through
SWIG at install time. `uv` downloads a `swig` *Python package* as a build
dependency, but `box2d-py` invokes `swig` as a command, so an interpreter-level
package does not satisfy it. The build needs the executable on `PATH`.

Nothing about PushT uses Box2D. It arrives through `gymnasium[all]` and the
install fails whether or not you will ever touch it.

```bash
uv tool install swig      # no root needed, lands in ~/.local/bin
sudo apt install swig     # or system-wide, if you have root
```

Then re-run `uv sync`. Machines differ here for no visible reason: TRUBA ships
SWIG 4.3.0 system-wide so it builds there with no intervention, while a stock
Ubuntu 22.04 desktop has none and fails. Measured on both.

### 2.1 Windows only: fix the CPU-only torch

**Verified on Ubuntu 24.04**: `uv sync` there installs `torch 2.11.0+cu130`
with `torch.cuda.is_available()` already `True`, so Linux users skip this whole
section. It really is Windows-specific.

Note the version though: Linux gets **cu130** and the Windows wheel below is
**cu128**. The lock pins the torch version, not the CUDA build, so a Windows and
a Linux teammate run different CUDA toolkits. See §6.4 for what that means for
comparing their numbers.

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
export STABLEWM_HOME="$HOME/inzva-hierarchical-planning/.stable-wm"
```

**Windows PowerShell**, current session only:

```powershell
$env:STABLEWM_HOME = "C:\path\to\inzva-hierarchical-planning\.stable-wm"
```

**Windows PowerShell**, persistent (do this one, the line above is forgotten when
you close the terminal):

```powershell
[Environment]::SetEnvironmentVariable("STABLEWM_HOME", "C:\path\to\inzva-hierarchical-planning\.stable-wm", "User")
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
| `kotmul/dinowm_patch_prop_pusht` | Community PreJEPA, epoch 10, ~11 downloads, no published number | **Use this for Experiment B**: 84.0% over 3 seeds (§11) |
| `kevin510/swm-dino-wm-checkpoints` | Raw hydra run dirs, wrong layout, 0 downloads | Ignore |

### Consequence for week 1

**Reproduce LeWM at 96%, not DINO-WM at 74%.** It is the only official
checkpoint, and it validates the eval config, the dataset and the solver exactly
as well as DINO-WM would — in a day rather than a training run.

DINO-WM stays the Experiment B comparison baseline. We first assumed that meant
**training it ourselves**, and budgeted for it. **It does not.** The kotmul
checkpoint above scores 84.0% under our protocol after three fixes, so we use it
as is (§11).

Training remains the fallback if that checkpoint is ever ruled out. In this repo
"DINO-WM" is PreJEPA with a frozen `dinov2_small` backbone:
`scripts/train/prejepa.py`, config `scripts/train/config/prejepa.yaml`.

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
| `eval.img_size` | 224 | decided; see below |
| `eval.eval_budget` | 50 | the budget the published table uses |
| `eval.num_eval` | 50 | episodes per run |
| `seed` | 42 | swept to `0,1,2` for anything reportable |

**Resolution is 224, everywhere, including the GRU models.** It is what the
dataset already stores, so there is no preprocessing step, and it is what
DINO-WM is locked to because DINOv2 requires that input size.

The reason it is not a free choice: Experiment A compares two planners on the
same world model, so resolution cancels out and 64 would be free speed. But
Experiment B compares our GRU against DINO-WM, and training ours at 64 turns
that into a comparison across two resolutions rather than two representations,
confounding the one thing B exists to measure. So the decision is made by what B
needs, not by what A needs.

The only cost is training throughput, roughly 12x against 64x64. Revisit it only
if GRU training proves too slow on TRUBA. If you do drop to 64, say plainly in
the report that Experiment B is confounded, or drop B.

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
| Different machine, same GPU model | Same, as far as we can tell. Still untested |
| Different GPU model | **Measured: at most 2 episodes in 150 differ.** See below |
| Windows vs Linux, same GPU | **Measured: 1 episode in 150 differs.** Better than expected, see below |

#### Three machines, three GPU generations, measured

The same three seeds, run on every machine we have. Nothing is shared between
them but the repo and the lockfile:

| Seed | Windows, RTX 3060 | TRUBA, V100 | Ubuntu, RTX A4000 |
|------|-------------------|-------------|-------------------|
| 0 | 42/50 | 42/50 | 42/50 |
| 1 | 48/50 | 47/50 | 47/50 |
| 2 | 41/50 | 41/50 | 42/50 |
| **Mean** | **87.3%** | **86.7%** | **87.3%** |

| | Windows | TRUBA | Ubuntu |
|---|---|---|---|
| GPU architecture | `sm_86` | `sm_70` | `sm_86` |
| torch | `2.11.0+cu128` | `2.11.0+cu126` | `2.11.0+cu130` |
| OS | Windows 11 | Rocky Linux 9.2 | Ubuntu 22.04 |

Records: `notes/results/inzva_pusht_results.md`, `truba_results.md`,
`a4000_results.md`.

The V100 was then run a second time, unchanged, and moved by 2 episodes of
150 (seed 1: 47 to 48, seed 2: 41 to 42). That is same-machine rerun noise,
not drift, and it matches the roughly 1.5% measured on Windows. Pooled over
both runs the V100 sits at **262/300 = 87.3%**, the same figure as Windows.
It is in `truba_results.md` as six rows rather than three, on purpose: the
repeat is evidence, not clutter.

No pair disagrees on more than 2 episodes of 150, and all three means land
within 0.6 points. That covers three CUDA major/minor builds, two GPU
generations including one that predates the others by four years, and two
operating systems.

This is the strongest version of the claim the section makes: **the three-seed
mean is portable**, and per-seed rates move by at most one episode. It does not
make the drift zero, and it is still one benchmark on one checkpoint, but the
"different GPU model" row above no longer has to be a guess.

Note the three torch builds. Every machine runs torch 2.11.0, and every machine
runs a *different CUDA build* of it, for reasons that are forced rather than
chosen: Windows installs its CUDA wheel out of band (§2.1), TRUBA needs cu126 or
it has no kernels for a V100 (§12.2), and a stock Linux box gets cu130 from the
lockfile. The lock pins the version, not the build, and that turns out not to
matter at the resolution we care about.

#### Windows against Linux, measured

Ubuntu 24.04 under WSL2, same GPU, installed from scratch by following §2:

| Seed | Windows (cu128) | Linux (cu130) | Episodes differing |
|------|-----------------|---------------|--------------------|
| 0 | 42/50 | 42/50 | 0 |
| 1 | 48/50 | 48/50 | 0 |
| 2 | 41/50 | 42/50 | 1 |

| | |
|---|---|
| Windows mean | 87.3% |
| Linux mean | 88.0% |
| Episodes differing | **1 of 150** |

This is better agreement than the row above originally predicted, and better
than two runs on the *same* Windows machine managed (2 of 150). The platforms
run different CUDA toolkits, different SDL builds and a different OS, and still
land on the same episodes almost everywhere.

Read it as reassurance with a caveat: it is one comparison on one GPU, and the
sample is small enough that 1 versus 2 differing episodes is not a real
difference. The honest summary is that cross-platform drift is **no worse** than
rerun noise, not that it is smaller.

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

## 6.5 Model decisions, and what they cost us

### Shared encoder: decided, share it and freeze it

**One encoder, trained with the fine model, then frozen. The coarse model
trains only a dynamics head on top of it.**

The reason is experimental rather than computational. Experiment A claims to
isolate the planner. If training the coarse model also updates the encoder, then
the fine model inside our method is no longer the fine model the baseline uses,
and A stops isolating anything. Freezing keeps row 2 and row 3 sharing a
bit-identical world model, so the only thing differing between them is the
solver, which is the entire claim.

It also makes waypoints mean something. Coarse and fine share one latent space,
so a coarse waypoint is directly a target the fine model can plan toward. With
separate encoders you would need a learned mapping between two latent spaces, or
the waypoint is gibberish to the fine model.

**The consequence, recorded now so nobody rediscovers it in week 3:** the
encoder is optimised for short-horizon prediction, because that is what the fine
model trains it for. Features that predict one step well are not necessarily the
features that predict eight steps well. **A frozen encoder may therefore cap how
good the coarse model can get**, and the cap is invisible: the coarse model will
simply be mediocre without telling you why.

Symptoms to watch for once the coarse model exists:

- Coarse validation loss plateaus early and well above the fine model's, after
  scaling for stride.
- Waypoints are reachable but not useful: the fine model hits them and the task
  still fails.
- Experiment A shows no benefit at any budget while `k = 1` passes Experiment C.
  That combination points at the representation, not the solver.

**If you unfreeze, you must retrain the baseline too.** Joint fine-tuning gives
the coarse model a representation suited to its own stride and may well be the
right call. But the moment the shared encoder changes, row 2's world model is no
longer row 3's, so the baseline has to be retrained and re-evaluated on the same
model or Experiment A stops being a planner-only comparison. That is roughly
double the training budget. Decide it deliberately, not by accident.

### Horizon, action block and k: locked

The three are bound together by an assertion in `scripts/plan/eval_wm.py:69`:

```text
horizon * action_block <= eval_budget        # eval_budget is 50
```

The current values (`horizon: 5`, `action_block: 5`) leave no room for a
hierarchy at all: a coarse stride of 4 over a 5-step horizon gives one waypoint.

`action_block: 5` is **not** binding on us. It is forced by the published
checkpoint's action encoder, which takes 10 inputs as 2 action dims times
frameskip 5 (§7). Our GRU is ours and can use a block of 1.

Locked, in `scripts/plan/config/inzva_gru.yaml`. It keeps the spec's framing of
five coarse decisions, at the horizon the flat planner actually handles (§13):

| Key | Value | Why |
|-----|-------|-----|
| `action_block` | 1 | ours to choose; the constraint came from someone else's checkpoint |
| `horizon` | 10 | measured best for the flat planner (§13); 10 x 1 = 10 <= 50 |
| `k` | 2 | 10 / 2 = 5 coarse waypoints, the spec's "5 decisions" |

> **Changed 2026-09-18, from `horizon: 40` and `k: 8`.** Those were derived from
> the method's shape, not measured. The evaluation goal is 25 steps ahead and
> `GoalMSE` scores only the last predicted step, so a 40-step horizon aims 15
> steps past the goal: the trained GRU scores 15.3% at 40 against 62.0% at 10.
> The waypoint count is unchanged at 5. Full reasoning and the sweep are in §13.

Two things to keep in mind about what this buys and costs:

- **The saving per plan is now small, and that is a real risk to Experiment A.**
  At `horizon: 10` and `k: 2`, flat CEM rolls 10 model steps per candidate while
  the hierarchy rolls 5 coarse plus 2 fine, about 7. At the old `horizon: 40`
  the gap was 40 against roughly 13. The hierarchy's advantage has to come from
  searching a smaller space, not from cheaper rollouts.
- **This is why Experiment A sweeps the sample budget.** If the two planners are
  close at every budget, that is a negative result and we report it (§0). The
  horizon sweep in §13 is the other axis worth having if compute allows.
- **Long rollouts compound model error.** This is measured now: the same model
  scores 62.0% at `horizon: 10` and 15.3% at 40 (§13). Both our planners meet at
  the same horizon, so the handicap is shared and cancels in Experiment A.

`k` is the natural thing to sweep. Try at least `{4, 8}`, and remember `k = 1` is
Experiment C and must score like the flat baseline.

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
- **Decompressing the dataset needs headroom, not just disk.** `zstd -d` on the
  13 GB archive writes 46 GB, and on WSL that filled the VM's page cache until
  the host OOM-killed it, twice. Two ways round it: lower the WSL memory cap
  first, or verify the archive without expanding it, which is enough to prove a
  download is good:

  ```bash
  zstd -t "$STABLEWM_HOME/datasets/pusht_expert_train.h5.zst"
  ```

  That checks zstd's own frame checksums and prints the decompressed size. Ours
  reports `46300921856 bytes`, and the archive itself is `13136247974` bytes,
  both matching the source exactly. A download that passes those two numbers
  does not need decompressing to be trusted.
- **16 GB of RAM is tight, and WSL makes it tighter.** Two things got
  OOM-killed on a 15.8 GB laptop during this work: loading the Lance dataset
  through the repo's reader (§5.2), and a `uv sync` running alongside a large
  download inside WSL. If you use WSL, check `~/.wslconfig` before you start:
  a `memory=12GB` line on a 16 GB host leaves Windows under 4 GB, and whichever
  side loses the race gets killed. Lower it to 8 GB, or run one heavy job at a
  time. The eval itself is fine; it is the concurrency that is not.
- **Spaces in the project path.** Most things cope, but Hydra config overrides and
  shell scripts sometimes do not. First suspect for any strange parse error.
- **Session-only env vars on Windows.** See section 3. Use the persistent form.
- **`uv sync` reverts the CUDA torch on Windows.** See section 2.1.

---

### 7.x `git pull` refuses because of `notes/results/`

```text
error: The following untracked working tree files would be overwritten by merge:
	notes/results/a4000_results.md
```

Expected, and harmless. `scripts/collect_results.py` writes into `notes/results/`
on the machine that ran the eval, where the file starts untracked. Once someone
commits that record, every machine that generated its own copy has an untracked
file sitting where a tracked one is about to land, and git refuses rather than
clobber it.

Delete your copies and pull; git holds the same content:

```bash
rm notes/results/<name>_results.md notes/results/<name>_results.json
git pull --ff-only
```

Check first if you want to be sure (`sha256sum` on both sides). This has been
identical every time so far, because the committed copy *is* the generated one.

**This bites hardest on a cluster.** A refused pull leaves the checkout on an
old commit while `sbatch` keeps working, so jobs quietly run stale code. Verify
the pull landed before submitting, not after.

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
- [x] **Image resolution decided: 224 everywhere** (§6.1)
- [x] **Shared encoder decided: share and freeze**, with the cap it implies
      and the cost of reversing it written down (§6.5)
- [x] **`k` = 8, horizon = 40, action_block = 1 locked** into
      `scripts/plan/config/inzva_gru.yaml` (§6.5)
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
- [x] Cold-start Linux test on Ubuntu 24.04 under WSL2: 88.0%, 1 episode in 150
      differing from Windows, and three more documentation bugs fixed (§9)
- [x] `.gitattributes` added; a Windows checkout is now pure LF, so Linux and
      macOS teammates see no phantom diffs
- [x] Pushed to `Thnorty/inzva-hierarchical-planning` (public)
- [x] **Reproduction closed** (§6.1b). 96% not reproducible; every mechanical
      explanation tested and eliminated; baseline of record is 87.3% ± 7.6
- [x] **TRUBA set up and verified** (§12): checkout, venv, dataset, and both
      checkpoints in place. Dataset fingerprint matches this file exactly.
      torch has to be the cu126 build there or it has no kernels for the GPUs
- [x] CPU preflight passes 8/8 on TRUBA (§12.2b), including headless
      rendering and the DINO-WM checkpoint, which needs a compute node
- [x] **Third machine tested cold** (Ubuntu 22.04, RTX A4000): found the
      `swig` build failure (§2.0b) and that the DINO-WM fix needed scripting
      (`scripts/adapt_dinowm.py`). Preflight 8/8, eval mean 87.3%
- [x] **Cross-machine agreement measured on three GPUs** (§6.4): at most 2
      episodes of 150 differ, all three means within 0.6 points
- [x] **Fine GRU written, trained and scored** (§10). 30 epochs, 7.5 h on an
      A4000. **62.0%** over two three-seed runs: the Experiment A baseline
- [x] **Planning horizon decided** (§13): `horizon: 10`, `k: 2`, still 5
      waypoints. The old 40 scored 15.3% because it aims past the goal
- [x] **Coarse model trained** (§10). Stride 2 on the fine model's frozen
      latent, 2.5 h. 74.7% planned alone, `notes/results/inzva_gru_coarse_results.md`
- [x] **Replanning interval measured** (§13): worth up to 16 points, and the
      coarse model's apparent lead over the fine one is mostly this
- [x] **DINO-WM scored: 84.0% over three seeds** (§11). The kotmul checkpoint
      runs after three fixes and is our Experiment B reference. We do not
      train DINO-WM ourselves

Open, in the order they block things:

- [ ] **Decide the replanning interval for our rows** (§13). The locked 5 was
      copied from upstream and never measured; 10 scores ~9 points higher for
      both our models. Whatever is chosen, flat and hierarchical planners must
      match in *environment* steps, or the hierarchy gets a free 10 points

- [ ] A **teammate** runs the five commands in §9. Done twice here already, in
      a fresh Windows clone and cold on Ubuntu under WSL2, catching five
      documentation bugs between them (§9). What neither could change is macOS,
      a different GPU, and a reader who did not write the document.
- [ ] **Six files assigned to five people** (`models/gru_wm.py`,
      `models/gru_coarse.py`, `solver/hierarchical.py`, `scripts/train_gru.py`,
      `scripts/sweep.py`, `README.md`)
- [ ] How many seeds the compute allows (3 is the floor)
- [ ] Experiment C (`k = 1`) scores like the GRU + CEM baseline — run this
      before A and B

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

We then did it again on **Ubuntu 24.04 under WSL2**, from a cold start: fresh
clone, fresh install, empty caches, dataset downloaded from scratch.

| Check | Result |
|-------|--------|
| Line endings on a Linux checkout | 296 files LF, **0 CRLF**, clean `git status` |
| §2.1's claim that Linux needs no torch swap | **True.** `uv sync` gives `2.11.0+cu130`, CUDA already available |
| Cold dataset download (§5) | 13,136,247,974 bytes, matching the source exactly; `zstd -t` confirms 46,300,921,856 decompressed |
| Cold checkpoint download | Fetched and loaded, via the v5 rename patch, which Linux needs too |
| Dataset checks | Identical to Windows, to the digit |
| Split fingerprint | `2d5f8c4f85e918f8`, matching |
| Three-seed mean | **88.0%** against Windows' 87.3%; 1 episode in 150 differed |

Further gaps it found, all fixed:

- **No way to authenticate.** The repo was private at the time and the README never said how
  to clone it. GitHub dropped password auth, so a fresh machine fails outright.
- **Stale paths after the rename.** §3 still said `stable-worldmodel` while §2
  cloned `inzva-hierarchical-planning`, which would put 46 GB outside the clone.
- **`zstd -d` gets OOM-killed** writing 46 GB under WSL's memory cap, which is
  how we learned `zstd -t` proves a download without expanding it.

What remains untested is macOS, a different GPU, and a person who did not write
the document trying to follow it.

---

## 10. The fine GRU: built, trained and scored

**Done.** Trained 30 epochs on an RTX A4000 in 7.5 hours; predicts the latent
24x better than assuming nothing moves. **Scores 62.0%** under the locked config,
pooled over two three-seed runs, which is the baseline Experiment A has to beat.
It scored 15.3% before the horizon was fixed (§13).

**Files:** `stable_worldmodel/wm/gru/gru_wm.py`, `scripts/train_gru.py`,
`scripts/train/config/gru.yaml`, `tests/wm/test_gru_wm.py`.

**The coarse model is done too** (`scripts/train/config/gru_coarse.yaml`): the
same architecture at stride 2 over the fine model's frozen latent, 2.5 h to
train because a frozen encoder needs no backward pass. Planned on its own with
plain CEM it scores 74.7%, but read §13 before comparing that with the fine
model's 62.0%: most of the gap is the replanning interval, not the stride.

```bash
python scripts/train_gru.py --config-name gru_coarse   # needs gru_fine first
```

Train it, or continue an interrupted run, with:

```bash
python scripts/train_gru.py                      # 30 epochs, ~7.5 h on an A4000
python scripts/train_gru.py train.precision=fp16 # V100/P100 have no bf16
```

It writes `weights.pt` for `policy=gru_fine`, a loadable snapshot per epoch under
`epochs/`, and resumes from `train_state.ckpt` if a cluster time limit kills it.

The model is **not** at `models/gru_wm.py` as the spec table says. A script run
from the repo root cannot import a root-level package, so `eval_wm.py` could
never load a checkpoint of a model defined there. It lives in the package
instead, beside `lewm`. The rest of this section is the contract the coarse
model has to satisfy too.

### The contract is two methods

To be driven by the existing CEM solver through `WorldModelPolicy`, a world model
needs to satisfy `stable_worldmodel.protocols.Dynamics`, which is exactly this:

```python
def encode(self, x: dict) -> dict:
    """Add latents to an observation dict (pixels, proprio -> emb)."""

def rollout(self, info_dict: dict, action_candidates: torch.Tensor) -> dict:
    """Roll candidates forward. action_candidates is (B, S, horizon, action_dim).
    Return the dict with predicted_emb of shape (B, S, H + horizon, dim),
    whose first H entries are the encoded context frames."""
```

It is a `runtime_checkable` `Protocol`, so there is nothing to subclass and
nothing to register. If you find yourself needing to modify the solver or
`WorldModelPolicy` to make your model fit, stop: that means the model is wrong,
not the harness.

### It must be loadable the way every other checkpoint is

`load_pretrained` reads `config.json`, calls `hydra.utils.instantiate` on it, and
then `load_state_dict`. So the class has to be constructible from a plain config
dict with a `_target_` key, the way `stable_worldmodel.wm.lewm.LeWM` is. Save
with `swm.wm.utils.save_pretrained(model, run_name, config=cfg)` and it writes
`weights.pt` plus `config.json` into `$STABLEWM_HOME/checkpoints/<run_name>/`.

Get this right from the first checkpoint. Retrofitting it later means retraining.

### Everything already decided, do not re-litigate

| Setting | Value | Where |
|---------|-------|-------|
| Resolution | 224 | §6.1 |
| Train/val split | seed `20260910`, 5% held out, fingerprint `2d5f8c4f85e918f8` | §6.2 |
| Encoder | one, shared, frozen after fine training | §6.5 |
| `action_block` | 1 | §6.5, `scripts/plan/config/inzva_gru.yaml` |
| `horizon` | 10 | same, and §13 |
| `k` | 2 | same, for the coarse model later |
| Eval protocol | inherited from `inzva_pusht.yaml`, unchanged | §6.1 |

Use the split from code, not by hand:

```python
from scripts.inzva_split import split_episodes
train_eps, val_eps = split_episodes(num_episodes=18685)
```

### How you know it works

In order, cheapest first. Do not skip to the last one.

1. **It loads.** `save_pretrained` then `load_pretrained` round-trips and the
   state dict matches.
2. **It satisfies the protocol.**
   `isinstance(model, stable_worldmodel.protocols.Dynamics)` is `True`, and
   `rollout` returns `predicted_emb` of the documented shape.
3. **It plans at all.** A laptop-scale smoke run finishes and beats random:

   ```bash
   python scripts/plan/eval_wm.py --config-name inzva_gru \
       policy=<your-run-name> eval.num_eval=4 \
       solver.num_samples=50 solver.n_steps=10
   ```

   That proves the pipeline, not the model. It is not a reportable number (§7).
4. **It scores.** Full protocol, three seeds, via the shared config. Record with
   `python scripts/collect_results.py --results-file inzva_gru_results.txt`.

That fourth number becomes the **baseline of record for Experiment A**, the thing
the hierarchical solver has to beat.

### Two things to keep in mind while building

- **Seed variance on PushT is 14 points** at 50 episodes (§6.1b). Any difference
  under roughly 5 points will not be distinguishable from noise at three seeds.
  That sets how large an effect Experiment A needs before it can claim anything,
  and it is worth knowing before you tune.
- **A 40-step rollout compounds model error.** Expect this GRU to score below the
  LeWM reference's 87%. That is fine and expected: Experiment A compares our two
  planners on our own stack, so a shared handicap cancels. Do not tune toward 87%.

### After this lands

`models/gru_coarse.py` (stride `k`, frozen encoder, dynamics head only), then
`solver/hierarchical.py`, then Experiment C (`k = 1`) as the correctness gate
before A or B mean anything.

Separately and in parallel, someone should start **DINO-WM training**
(`scripts/train/prejepa.py`). It is needed for Experiment B, nobody has started
it, and it is the item most likely to run out of calendar. If four weeks gets
tight, B is the one to cut.

---

## 11. DINO-WM: there is a checkpoint, and it loads

§6 said no DINO-WM checkpoint exists in the layout `load_pretrained` expects.
That was too pessimistic. **`kotmul/dinowm_patch_prop_pusht` works**, after two
fixes. If it also performs, Experiment B needs no training run at all.

What it is: `_target_: stable_worldmodel.wm.PreJEPA`, frozen `dinov2_small`
backbone, patch tokens, `history_size: 3`, frameskip 5, action encoder with
`in_chans: 10` (2 dims x 5), trained on `swm/PushT-v1`. Same conventions as the
LeWM checkpoint. Published 2026-07-13, marked epoch 10, no published score.

### Fix 1: drop the `pixel_token` key

Its `config.json` carries `"pixel_token": "patch"`, which is not an argument of
this repo's `PreJEPA.__init__`. `git log -S pixel_token` finds nothing in
`wm/prejepa/`, so the checkpoint came from a fork, not from upstream. Loading it
raw fails:

```text
Error in call to target 'stable_worldmodel.wm.prejepa.prejepa.PreJEPA':
TypeError("PreJEPA.__init__() got an unexpected keyword argument 'pixel_token'")
```

Copy the cached checkpoint, delete that one key from `config.json`, and it loads
**strictly**: 302 of 302 tensors, zero missing, zero unexpected, zero shape
mismatches. Every other key in its config matches this repo's signature exactly.

```bash
cp -r "$STABLEWM_HOME/checkpoints/models--kotmul--dinowm_patch_prop_pusht" \
      "$STABLEWM_HOME/checkpoints/dinowm_kotmul_adapted"
python -c "
import json, pathlib, os
p = pathlib.Path(os.environ['STABLEWM_HOME'])/'checkpoints'/'dinowm_kotmul_adapted'/'config.json'
c = json.load(open(p)); c.pop('pixel_token', None); json.dump(c, open(p,'w'), indent=2)"
```

### Fix 2: use the PreJEPA objective, not the default

The default `goal_mse` scores the fused latent and dies:

```text
RuntimeError: The expanded size of the tensor (404) must match the existing
size (394) at non-singleton dimension 4
```

404 is 384 pixels + 10 proprio + 10 action; 394 is the same without action. A
goal prescribes a state, not an action, so the fused tensor cannot be scored
directly. The repo already ships the right objective and documents it for this
exact model:

```bash
objective=goal_mse_pixels_proprio
```

### Fix 3: stack proprio over history, not just pixels

Fixes 1 and 2 get it to start. It then dies partway into the first episode:

```text
RuntimeError: Sizes of tensors must match except in dimension 3.
Expected size 3 but got size 1 for tensor number 1 in the list.
```

`WorldModelPolicy` stacks only `pixels` over the last `history_len` block
timesteps (`policy.py:344`, `history_keys=('pixels',)`), and `eval_wm.py` never
passed anything else. PreJEPA reads proprio through a **per-frame** extra
encoder, so it needs one proprio vector per context frame.

The reason it starts and then fails is the nastiest part. At `t=0` the history
holds a single frame, so pixels and proprio both arrive as 1 and agree. The
history then grows to `history_len`, pixels become 3, proprio stays 1, and the
model's own `torch.cat` fails. **At the shared protocol that first planning call
takes 3.9 hours**, so the crash lands hours in and looks like a long run dying
for no reason.

`eval_wm.py` now forwards a `history_keys` config key, and
`scripts/plan/config/inzva_dinowm.yaml` sets it. Use that config rather than
assembling the overrides by hand:

```bash
python scripts/plan/eval_wm.py --config-name inzva_dinowm -m     policy=dinowm_kotmul_adapted seed=0,1,2
```

It also selects `goal_mse_pixels_proprio`, so fix 2 is no longer something to
remember either. Leave `history_keys` alone for LeWM: that model takes no
per-frame proprio, and `inzva_pusht.yaml` deliberately does not set it.

### It costs roughly 2.5 to 5 GPU-hours per seed, depending on the card

At the shared protocol:

| | LeWM, one env, one plan | DINO-WM, one env, one plan | DINO-WM, one seed, 50 eps |
|---|---|---|---|
| RTX A4000 | ~1 s | 282 s | **4.5 to 5.1 h, measured** |
| Tesla V100 | ~1 s | **145 s** | ~2.5 h, estimated |

The V100 is 1.9x faster here despite being the older card, because this
workload is memory-bandwidth bound rather than compute bound: 900 GB/s against
448. Worth knowing before assuming a newer GPU is the faster one.

An episode needs at most 2 plans (`horizon 5` x `action_block 5` = 25 env steps
against a 50-step budget), and the solver plans for all environments in one
call. **The first solve covers every environment; the second only replans the
ones that have not already succeeded**, so it is far shorter. On seed 0 the two
took 3.9 and 0.6 hours. We had estimated 7.8 hours per seed by assuming both
solves cover all fifty; that was wrong, and so was the conclusion drawn from it.

The V100 figure scales the A4000 measurement by the per-environment ratio and
has not been run end to end. On paper it fits inside the `debug` partition's
4-hour ceiling, but seeds here varied by 13% and the A4000 slowed further when
it ran hot, so treat `debug` as worth a try when the queue is long, not as a
safe default. `akya-cuda` remains the reliable choice.

The solver runs `batch_size: 1`, one environment at a time, so wall time scales
with `eval.num_eval` and memory does not. DINO-WM needs **8.6 GB for a single
environment**, so batching two would want ~17 GB and does not fit a 16 GB card.
Both the A4000 and the TRUBA V100s are 16 GB, so neither can batch it.

Plan Experiment B around that number. One job per seed on `akya-cuda`, which
allows 3 days; three concurrent jobs finish in the time of one seed, and
`slurm/eval.slurm` gives each its own results file so they cannot corrupt one
another.

### Run it on a server, not a laptop

```bash
python scripts/plan/eval_wm.py --config-name inzva_dinowm -m \
    policy=dinowm_kotmul_adapted seed=0,1,2
```

Use `inzva_dinowm`, not `inzva_pusht` with overrides. It carries fixes 2 and 3,
so there is nothing to remember at the command line.

**This does not fit a 6 GB laptop GPU.** It exhausted 16 GB of host RAM and had
to be killed before finishing 10 episodes. DINO-WM is far heavier than LeWM:
`dinov2_small` gives 256 patches x 384 dims per frame against ViT-tiny's 192, so
one frame of latents is roughly 414 KB per candidate (§7). Use TRUBA, or any
16 GB card: the scored run above was an RTX A4000.

### Its score: 84.0%, and we use it

Scored on 17 September 2026 under the shared protocol with `inzva_dinowm.yaml`,
on an RTX A4000. Record: `notes/results/dinowm_romer_results.md`.

| Seed | Success |
|------|---------|
| 0 | 45/50 |
| 1 | 41/50 |
| 2 | 40/50 |
| **Mean** | **84.0%**, spread 5.3 |

The worry that an epoch-10 checkpoint might be undertrained did not bear out. It
lands ten points above the 74% most often cited for this same protocol, inside
the 84% to 92% band that independent reruns report (section 07 of
`notes/inzva-project-spec.html`), and 3.3 points below our LeWM baseline, which
is inside seed noise at three seeds.

**Decision: this checkpoint is the Experiment B reference, and we do not train
DINO-WM.** Report it as this checkpoint rather than as DINO-WM in general. It came
from a fork of the harness and is marked epoch 10, so it is not the artifact
behind the published 74%.

## 12. TRUBA (the ARF cluster)

The cluster is set up and verified. `ssh truba` needs the VPN up first; the
usage notes for the account live in `~/truba_guide.md` on the cluster itself.

| | |
|---|---|
| Checkout | `/arf/scratch/$USER/inzva-hierarchical-planning` |
| `STABLEWM_HOME` | `.stable-wm` inside it, same as everywhere else |
| GPUs | `akya-cuda`: 4x V100 16GB. `barbun-cuda`: 2x P100 16GB |
| Wall clock | 3 days on the GPU partitions, 4 hours on `debug` |

Three cluster rules cause most first-day failures:

1. **Jobs must be submitted from under `/arf/scratch`.** A submit plugin rejects
   anything else with a Turkish error that does not say so in English.
   `slurm/submit.sh` sets `--chdir` for you.
2. **Omitting `--time` kills the job after two minutes**, and the GPU partitions
   reject any job without `--gres=gpu:N`.
3. **`/arf/scratch` is wiped after roughly a month and nothing is backed up.**
   Trained checkpoints must be copied to `/arf/home` or pulled down. The dataset
   is disposable; it is a re-download, not a loss.

### 12.1 Submitting

```bash
slurm/submit.sh slurm/eval.slurm --export=ALL,POLICY=quentinll/lewm-pusht
slurm/submit.sh slurm/eval.slurm \
    --export=ALL,POLICY=dinowm_kotmul_adapted,OBJECTIVE=goal_mse_pixels_proprio
```

`slurm/eval.slurm` documents the variables it accepts. It defaults to the
`debug` partition, whose GPU nodes are a subset of `akya-cuda`, because it
reaches the front of the queue sooner. Use `-p akya-cuda -t 1-00:00:00` for
anything that will not finish inside four hours.

The GPU queue is genuinely busy. Expect to wait, and prefer one job that does
three seeds over three jobs that each do one.

**Ask for the time you need, not the maximum.** The scheduler backfills short
jobs into gaps it is holding open for large ones, so a job that asks for 45
minutes can start hours before an identical job that asks for the partition
limit. The LeWM eval at three seeds takes about fifteen minutes:

```bash
slurm/submit.sh slurm/eval.slurm -t 00:45:00 --export=ALL,POLICY=quentinll/lewm-pusht
```

Being killed at the limit loses the whole run, so leave real headroom, and do
not trim the limit on a job whose runtime you have not measured yet. DINO-WM is
far heavier than LeWM and has no measured time at all.

**Always submit through `slurm/submit.sh`.** `sbatch` reads its command line as
`sbatch [options] script [job args]`, so anything written after the script path
goes to the job instead of to the scheduler. Written as bare `sbatch`, this

```bash
sbatch slurm/eval.slurm --export=ALL,POLICY=quentinll/lewm-pusht   # WRONG
```

drops the `--export` without a word, and the job then fails on an unset
`POLICY`. A `-t` in that position is ignored equally quietly, and the job simply
keeps the time limit the script declared, which is how you end up waiting hours
for a run you thought you had shortened. The wrapper reorders the arguments so
this cannot happen.

### 12.2 torch must be the cu126 build

**This is the one thing that will not work if you follow section 2 blindly.**
`uv sync` installs `torch 2.11.0` from PyPI, which is a CUDA 13 build. CUDA 13
dropped Maxwell, Pascal and Volta, so it has no kernels for either GPU here:

```text
archflags: sm_75 sm_80 sm_86 sm_90 sm_100 sm_120     # cu130 and cu128
archflags: sm_50 sm_60 sm_70 sm_75 sm_80 sm_86 sm_90 # cu126
```

The V100 is `sm_70` and the P100 is `sm_60`, so only the cu126 build runs here.
It is the **same torch version**, so nothing diverges from the rest of the team
except the CUDA variant:

```bash
uv sync --extra all --group dev
uv pip install --index-url https://download.pytorch.org/whl/cu126 \
    "torch==2.11.0+cu126" "torchvision==0.26.0+cu126"
```

Install torchvision explicitly with the `+cu126` suffix. Naming it without the
suffix is not enough: the version number already matches, so the resolver keeps
the CUDA 13 build it already has, and then the first import fails with

```text
RuntimeError: operator torchvision::nms does not exist
```

which reads like a missing package rather than a mismatched one.

Check it with the compile-time flags, not `torch.cuda.get_arch_list()`. The
latter returns `[]` on a login node because there is no GPU there, which looks
identical to "no kernels":

```bash
python -c "import torch; print(torch._C._cuda_getArchFlags())"
```

### 12.2b Check before you queue

```bash
slurm/submit.sh slurm/smoke.slurm
```

`scripts/preflight.py` verifies the torch build, the dataset fingerprint,
both checkpoints, headless rendering and both eval configs, all on CPU. The
job asks for no GPU, so it lands on an idle node and answers in about a
minute even when every V100 is allocated and a GPU job is quoting a start
time eleven hours out. Run it after any change to the environment, and after
a fresh clone on any machine, not only on TRUBA.

It reports 8/8 on the cluster today.

The torch check needs to know what it is checking against. Given a GPU it
reads the device capability; with no GPU it uses `PREFLIGHT_REQUIRE_ARCH`,
which the smoke job sets to `sm_70`.

### 12.3 Headless rendering

Compute nodes have no display and PushT renders through pygame, so jobs need
`SDL_VIDEODRIVER=dummy`. `slurm/truba_env.sh` exports it along with the rest of
the per-node settings. Source that file in any new job script rather than
re-deriving it.

### 12.4 Do not run models on the login node

`arf-ui1` is shared and limited. Loading the DINO-WM checkpoint there segfaults
after the DINOv2 backbone downloads. Small checks are fine; anything that builds
a model belongs in a job, per the cluster's own guidance.

## 13. The planning horizon: why it is 10 and not 40

**Decided 2026-09-18: `horizon: 10`, `k: 2`.** Set in
`scripts/plan/config/inzva_gru.yaml` and recorded in §6.5. This section is why.

### What the horizon is

Before the robot moves, the planner imagines what would happen if it took some
sequence of actions. The horizon is how many steps ahead it imagines. A horizon
of 40 plans 40 steps ahead; a horizon of 10 plans 10 steps ahead.

We locked 40 because the hierarchy needs it: 40 steps split into 5 waypoints of
8 steps each (§6.5). That number came from the design of our method, not from
testing how well anything plans with it.

### The problem

In evaluation, the planner is shown the state **25 environment steps ahead** and
told to reach it (`eval.goal_offset_steps: 25`). `GoalMSE` scores a candidate
plan on **one** thing: where it ends up on the *last* imagined step.

So with `horizon: 40` the planner chooses actions that put the block in the right
place at step 40, when the target was where things should be at step 25. It aims
15 steps past the finish line. LeWM does not have this problem: its
`horizon: 5` x `action_block: 5` is 25 environment steps, landing exactly on the
goal.

Two further effects pull the same way. Predictions drift the further ahead the
model imagines, and the planner must search a much larger space of action
sequences (40 choices instead of 10) with the same number of samples.

### Measured

Same trained model, same protocol, only `plan_config.horizon` changed. Seed 0:

| Horizon | 5 | 10 | 15 | 20 | 25 | 40 |
|---------|---|----|----|----|----|----|
| Success | 50% | **60%** | 40% | 22% | 24% | 14% |

At three seeds:

| Configuration | Seeds 0, 1, 2 | Mean | Record |
|---|---|---|---|
| `horizon: 40` | 10%, 22%, 14% | 15.3% | `notes/results/gru_horizon40_results.md` |
| `horizon: 10`, first run | 58%, 62%, 60% | 60.0% | superseded, see below |
| `horizon: 10`, locked config | 64%, 70%, 58% | 64.0% | `notes/results/inzva_gru_results.md` |

**Pooled over both horizon-10 runs: 62.0%, spread 4.6, range 58% to 70%.** Quote
that, not either run alone.

Those two runs are the same model, the same config and the same seeds, and they
differ by 8 episodes of 150. That is much larger than the 1 to 2 episodes a LeWM
rerun moves (§6.4), so **our GRU's planning is noisier run to run than the
reference model's**. An early reading of the first run as "far steadier across
seeds, spread 2.0" did not survive the second: that 2.0 was one lucky draw, and
the honest seed spread here is around 5 points, in the same range as LeWM's 7.6
and DINO-WM's 5.3. It matters because seed spread sets how large an effect
Experiment A has to produce before it can claim anything (§6.1b).

`horizon` must stay at or above `receding_horizon` (5). A run at 3 fails.

### What we decided, and why

Experiment A compares flat CEM against our coarse-to-fine solver. Pinned at
`horizon: 40`, the flat baseline would be a setting we had already measured as
bad, and beating it would prove little. **A fair Experiment A compares the
hierarchy against the best flat configuration**, so we moved the horizon to
where the flat planner is actually good.

`horizon: 10` with `k = 2` keeps the spec's five waypoints and changes nothing
about the method: the coarse model still plans 5 strided steps and the fine
model still fills the gaps. Only the size of the gaps changed, from 8 steps to
2.

**The baseline of record for Experiment A is 62.0%**, pooled over the two
horizon-10 runs above. `notes/results/inzva_gru_results.md` is the canonical
record, reproducible with the documented command. The 15.3% run is kept as
`notes/results/gru_horizon40_results.md`: it is what the old config produced
and is the evidence for this section, not a number to quote.

Two consequences worth carrying forward:

- **Do not raise the horizon to make the hierarchy look better.** The two
  planners have to meet at the same horizon, and that horizon has to be one the
  flat planner handles well.
- **A horizon sweep is still the most informative version of Experiment A.**
  The collapse from 60% to 14% as the horizon grows is exactly the weakness the
  hierarchy claims to fix. We rejected it on compute, not on merit; revisit it
  if the budget allows.

### The same trap again: the replanning interval

`receding_horizon: 5` is inherited from `inzva_pusht.yaml`, where it was copied
from upstream's PushT config. Like `horizon: 40`, nobody measured it against our
model. It is worth up to 16 points.

The planner plans `horizon` steps and then executes only `receding_horizon` of
them before replanning. **Replanning less often scores better here, for both of
our models**, which is the opposite of the usual expectation that more feedback
helps. Three seeds each:

| Environment steps executed per plan | 4 | 5 (locked) | 7 | 10 |
|---|---|---|---|---|
| Fine model, `horizon: 10` | — | 62.0% | 64.7% | **71.3%** |
| Coarse model, `horizon: 5`, `k = 2` | 58.7% | — | 68.0% | **74.7%** |

Read the columns, not the rows: the two models are close at every matched
cadence. The coarse model's headline 74.7% comes mostly from executing 10
environment steps per plan, not from temporal abstraction. Its default
`receding_horizon: 5` means 5 coarse steps, which is 10 environment steps,
while the fine model's 5 means 5.

**This matters for Experiment A more than the raw numbers do.** Any comparison
between the flat planner and the hierarchy has to hold the replanning interval
fixed *in environment steps*, or the hierarchy inherits a 10-point advantage
that has nothing to do with the method. A coarse or hierarchical planner that
keeps `receding_horizon: 5` in its own step units is silently replanning half as
often as the flat baseline.

Why longer intervals win is not established. A plausible reading is that CEM
re-solves from scratch each time, so frequent replanning resamples a noisy
20-dimensional search and can replace a good plan with a worse one, while the
model is accurate enough over 10 steps that the original plan survives contact
with the environment. That is a hypothesis, not a measurement.

### What is still unmeasured

`num_samples: 300` and `n_steps: 30` are also inherited rather than chosen, and
Experiment A sweeps the sample budget anyway. Nobody has checked whether our
models want a different CEM budget than LeWM did. Expect the same pattern:
settings picked for someone else's model are not automatically right for ours.
