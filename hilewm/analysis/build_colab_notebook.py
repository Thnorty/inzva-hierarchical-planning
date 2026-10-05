"""Generate `analysis/colab_setup.ipynb`.

The notebook is generated rather than hand-edited because the first version was
written by hand and was **syntactically broken**: its `source` lists carried no
trailing newlines, so Jupyter concatenated every line of six code cells into one
(`!nvidia-smiimport torch`). Writing the cells as real text and splitting them
here makes that class of bug impossible, and the validation at the bottom fails
the build if that or a use-before-assignment ever reappears.

    python analysis/build_colab_notebook.py

Edit this file, never the notebook.

Rewritten 2026-09-26 after the first live session, which found nine mismatches
between the released artifact and the released `stable_worldmodel` 0.1.1 before
the eval would run at all. Every one is handled here, in the cell where it bites,
with the evidence beside it. `docs/FINDINGS.md` has the long form.

Two rules for editing:

- never put a triple-quote inside a `code(...)` block: it closes the generator's
  own string. Use `#` comments.
- to emit a `\n` escape inside notebook source, write `\\n` here.
"""
import ast
import builtins
import json
import re
import sys
from pathlib import Path

cells = []


def md(text: str) -> None:
    cells.append({"cell_type": "markdown", "metadata": {}, "source": _src(text)})


def code(text: str) -> None:
    cells.append({"cell_type": "code", "execution_count": None, "metadata": {},
                  "outputs": [], "source": _src(text)})


def _src(text: str) -> list[str]:
    lines = text.strip("\n").split("\n")
    return [ln + "\n" for ln in lines[:-1]] + [lines[-1]]


# ---------------------------------------------------------------- 0. overview --

md("""
# Hi-LeWM on Colab — setup and the first success rate

Produces **one evaluation number of our own**: Hi-LeWM online, plain CEM, PushT,
goal offset d = 50, at the paper's Table 5 budget, 50 episodes, seed 42. That is
the cell the paper reports as **38.7 %**, and we have never had a success rate of
our own — every other finding in this project is about what the planner searches,
not how well it controls.

**Before you start**

1. In Google Drive, `inzva-final` must contain `code/`, `analysis/` and either
   `checkpoints/` with the weights **or** `checkpoints.zip` (step 2 takes either).
   The dataset is *not* uploaded — it is downloaded here.
2. `analysis/` in Drive must be the **current** copy from the repo: step 5 checks
   this and stops if it is stale, because three of the nine fixes live there.
3. Runtime -> Change runtime type -> **L4 or A100**. The eval config hardcodes
   `device: "cuda"`, so a GPU is required.

**Run the cells in order.** Expect ~60-75 minutes to the first number on a fresh
session, of which 45-55 minutes is the dataset download. If the runtime restarts,
use the **appendix** cell at the bottom rather than rerunning everything.

### What this notebook works around

Nine mismatches stand between the released artifact and the released
`stable_worldmodel` 0.1.1. All nine were found on 2026-09-26; each is handled in
the step named here and documented in `docs/FINDINGS.md`.

| # | what breaks | handled in |
| --- | --- | --- |
| 1 | `environment-gpu.yml` omits the `format` extra, but `formats/hdf5.py` imports `hdf5plugin` unconditionally and the PushT pixels are blosc-compressed | step 3 |
| 2 | `transformers >= 5.9` removed the ten `modeling_vit` classes the pickled checkpoints name | step 3 |
| 3 | `h_le_wm/config/*` ships without `__init__.py`, so Hydra cannot resolve `config_path="../config/eval"` | step 5 |
| 4 | the dataset is written to `$STABLEWM_HOME/` and read from `$STABLEWM_HOME/datasets/` | step 7 |
| 5 | checkpoints are staged to `$STABLEWM_HOME/runs/` and loaded from `$STABLEWM_HOME/checkpoints/runs/` | step 9 |
| 6 | `CEMSolver` reads the env count off a string, so the hierarchical planner runs at no env count | step 11, via `analysis/run_eval.py` |
| 7 | the eval never registers the `hi_jepa` pickle aliases that its sibling train module registers | step 11, via `analysis/run_eval.py` |
| 8 | `World.evaluate_from_dataset` does not exist in 0.1.1 | step 11, via `analysis/run_eval.py` |
| 9 | the eval config passes `world.history_size` / `world.frame_skip`, which `PushT` rejects | step 13, deleted with Hydra `~key` |

Two more are not ours to fix: the flat baseline conversion fails on upstream drift
(step 8, non-fatal), and `validate checkpoints` cannot be narrowed to one
checkpoint (step 10).
""")

# ------------------------------------------------------------------ 1. GPU -----

md("""
## 1. Check the GPU

An L4 is enough: the first session peaked at **409 MiB of 15360** with 50
environments, so memory is not the constraint. Compute is.
""")

code("""
!nvidia-smi

import torch
print("torch:", torch.__version__, "| cuda:", torch.cuda.is_available())
print("device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "-")
assert torch.cuda.is_available(), "No GPU. Runtime -> Change runtime type -> L4/A100, then rerun."
TORCH_BEFORE_INSTALL = torch.__version__
""")

# --------------------------------------------------- 2. Drive and checkpoints --

md("""
## 2. Mount Drive, find the artifact, resolve the checkpoints

Change `ARTIFACT` if the folder sits elsewhere in Drive.

The three files this session stages are resolved **by name**, with a fallback to
`checkpoints.zip`. Both halves were learned the hard way: the first Drive copy held
the checkpoint directory tree and its `config.yaml` files and **none of the
weights** — a 2 GB upload that silently skipped every large file — while
`checkpoints.zip` sat beside it intact. And the cell that needed the files used to
come *after* the 45-minute dataset download, so the mistake cost a download to
discover. Keeping only `checkpoints.zip` in Drive is in fact the better state: one
file instead of 76.
""")

code("""
from google.colab import drive
drive.mount('/content/drive')

import shutil, time, zipfile
from pathlib import Path

ARTIFACT = Path('/content/drive/MyDrive/inzva-final')   # <-- edit if needed
CODE     = ARTIFACT / 'code'
ANALYSIS = ARTIFACT / 'analysis'
CKPTS    = ARTIFACT / 'checkpoints'

for p in (ARTIFACT, CODE, ANALYSIS):
    assert p.exists(), f"Not found: {p}  (check the ARTIFACT path above)"

ZIP = ARTIFACT / 'checkpoints.zip'
LOCAL_CKPTS = Path('/content/ckpts')       # local disk: fast, and Drive stays clean

MEMBERS = {
    'hi': 'checkpoints/pusht/main/pusht_hi_lewm_epoch15_object.ckpt',
    'probe_a': 'checkpoints/pusht/probes/phase_a/pusht_decoder_probe_phase_a.pt',
    'probe_b': 'checkpoints/pusht/probes/phase_b/pusht_decoder_probe_phase_b.pt',
}
EXPECTED_MB = {'hi': 122, 'probe_a': 18, 'probe_b': 18}


def resolve_checkpoints():
    # -> {key: Path}, from the Drive tree, a previous extraction, or the zip.
    out, missing = {}, {}
    for key, member in MEMBERS.items():
        hits = [h for h in sorted(ARTIFACT.rglob(Path(member).name)) if h.is_file()]
        local = LOCAL_CKPTS / member
        if hits:
            out[key] = hits[0]
        elif local.is_file():
            out[key] = local
        else:
            missing[key] = member
    if not missing:
        return out

    print("missing from Drive, taking them from checkpoints.zip:")
    for member in missing.values():
        print("   ", member)
    assert ZIP.is_file(), (
        f"{ZIP} not found either. Upload checkpoints.zip, or the three files under "
        "MEMBERS, to Drive and rerun this cell.")
    print(f"zip: {ZIP.stat().st_size/1e9:.2f} GB")

    # Copy first: random access into a 2 GB file over the Drive mount is slow and
    # occasionally flaky, while a sequential copy is neither.
    zip_local = LOCAL_CKPTS / 'checkpoints.zip'
    zip_local.parent.mkdir(parents=True, exist_ok=True)
    if not zip_local.is_file() or zip_local.stat().st_size != ZIP.stat().st_size:
        t0 = time.time()
        shutil.copy2(ZIP, zip_local)
        print(f"copied to local disk in {time.time()-t0:.0f} s")

    with zipfile.ZipFile(zip_local) as z:
        names = set(z.namelist())
        absent = [m for m in missing.values() if m not in names]
        assert not absent, f"not in the zip: {absent}"
        t0 = time.time()
        z.extractall(LOCAL_CKPTS, members=list(missing.values()))
        print(f"extracted in {time.time()-t0:.0f} s")

    # Free the 2 GB again: step 6 wants 62 GB for the dataset, and re-copying from
    # Drive costs seconds if another member is ever needed.
    zip_local.unlink(missing_ok=True)

    for key, member in missing.items():
        out[key] = LOCAL_CKPTS / member
    return out


resolved = resolve_checkpoints()
CKPT_HI = resolved['hi']
CKPT_PROBE_A = resolved['probe_a']
CKPT_PROBE_B = resolved['probe_b']

print()
for key, f in resolved.items():
    mb = f.stat().st_size / 1e6
    ok = abs(mb - EXPECTED_MB[key]) < 2
    print(f"  {'OK ' if ok else '?? '} {key:8s} {mb:7.1f} MB  {f}")
    assert ok, f"{key} is {mb:.1f} MB, expected ~{EXPECTED_MB[key]} MB (truncated upload?)"
""")

# ------------------------------------------------------------- 3. install ------

md("""
## 3. Install dependencies

Colab has no conda, so `environment-gpu.yml` cannot be used directly — and its pip
payload (`stable-worldmodel[train,env]`) is wrong for us in both directions.

**`[format]` is missing and is mandatory** (mismatch 1).
`stable_worldmodel/data/formats/hdf5.py:11` imports `hdf5plugin` unconditionally,
and the PushT `pixels` column really is blosc-compressed — HDF5 filter id 32001,
read off our own copy of the dataset. Without it the dataset cannot be opened.

**`[env]` is far more than we need.** It pulls `gymnasium[all]` (box2d, hence a
swig build), `ogbench`, `craftax` (jax), `ale-py`, `gymnasium-robotics`.
`stable_worldmodel/envs/__init__.py` only registers entry points as strings, so
nothing is imported until `make()`; `swm/PushT-v1` needs exactly `cv2`,
`gymnasium`, `pygame`, `pymunk` (`envs/pusht/env.py:1-8`).

**`[train]` is needed**: the eval reads `spt.data.dataset_stats.ImageNet`
(`h_le_wm/eval/hierarchical.py:292`), and Hydra and scikit-learn arrive with it.

**`transformers` must be pinned below 5.9** (mismatch 2). The `*_object.ckpt` files
are pickled model objects naming ten classes from
`transformers.models.vit.modeling_vit` — `ViTModel`, `ViTEncoder`, `ViTLayer`,
`ViTAttention`, `ViTSelfAttention`, `ViTSelfOutput`, `ViTIntermediate`,
`ViTOutput`, `ViTEmbeddings`, `ViTPatchEmbeddings` (read out of our own copy with
`pickletools`). That structure was removed in **5.9.0** — present in 5.8.0, gone in
5.9.0, and 5.17 is what a current Colab installs, since `stable-worldmodel` asks
only for `>=4.50.0`. Without the pin `torch.load` raises `AttributeError: Can't get
attribute 'ViTEncoder'`, and the eval loads the same file, so it blocks everything.
`transformers==4.57.6` is the era-matched fallback.

Two things to watch:

- If pip replaces Colab's torch, CUDA can break. The cell prints the version before
  and after and fails loudly if it moved.
- If Colab asks you to **restart the runtime**, restart and use the appendix cell.
""")

code("""
!pip install -q "stable-worldmodel[train,format]" pygame pymunk shapely opencv-python-headless zstandard
!pip install -q "transformers>=4.50,<5.9"
!apt-get -qq install -y zstd > /dev/null 2>&1 || echo "(apt zstd unavailable; python zstandard will be used)"

import importlib, importlib.metadata as md
import sys
import torch

print()
for pkg in ["stable-worldmodel", "stable-pretraining", "transformers", "torch",
            "torchvision", "lancedb", "pylance", "hdf5plugin", "h5py", "gymnasium",
            "hydra-core", "scikit-learn", "numpy"]:
    try:
        print(f"  {pkg}=={md.version(pkg)}")
    except md.PackageNotFoundError:
        print(f"  {pkg}  *** MISSING ***")

print()
print("python:", sys.version.split()[0])
before = globals().get('TORCH_BEFORE_INSTALL')   # undefined after a restart
print("torch before install:", before, "-> now:", torch.__version__)
if before is not None:
    assert torch.__version__ == before, (
        "pip replaced Colab's torch; CUDA may be broken. Reinstall the Colab torch "
        "build, or pin torch in the install line above.")
assert torch.cuda.is_available(), "CUDA disappeared after the install."

# The imports that fail first when something is wrong, in the order they matter.
import hdf5plugin            # noqa: F401  blosc filter for the PushT pixels
import stable_worldmodel     # noqa: F401  uninstallable on the Intel Mac; must work here

# Mismatch 2, checked here instead of at load time: the object checkpoint is a
# pickled model, so every class it names must exist in the installed transformers.
import transformers
import transformers.models.vit.modeling_vit as mv

NEEDED_VIT = ('ViTModel', 'ViTEncoder', 'ViTLayer', 'ViTAttention', 'ViTSelfAttention',
              'ViTSelfOutput', 'ViTIntermediate', 'ViTOutput', 'ViTEmbeddings',
              'ViTPatchEmbeddings')
absent = [c for c in NEEDED_VIT if not hasattr(mv, c)]
print("transformers:", transformers.__version__, "| missing ViT classes:", absent or "none")
assert not absent, (
    f"transformers {transformers.__version__} dropped {absent}; the pickled "
    "checkpoints cannot be unpickled. If the version printed is already < 5.9 the "
    "old module is still cached in this kernel: restart the runtime and continue "
    "from the appendix cell.")

importlib.import_module("stable_pretraining")
# `spt.data` is the import that fails on the Mac (torchvision 0.17.2 has no
# transforms.v2.GaussianNoise); the eval needs it for the ImageNet statistics.
importlib.import_module("stable_pretraining.data")
print()
print("stable_worldmodel and stable_pretraining.data both import. Good.")
""")

# ---------------------------------------------------------- 4. upstream clone --

md("""
## 4. Clone the upstream LeWorldModel source — optional

The artifact deliberately does not redistribute it; it belongs at
`code/third_party/lewm`. **Only the flat baseline path needs it**
(`h_le_wm/baseline/adapter.py:12`, `h_le_wm/eval/baseline_manifest.py:27`); the
Hi-LeWM eval never imports it. Since the baseline conversion is broken anyway
(step 8), this cell is non-fatal.

`THIRD_PARTY_LEWM.md` mentions a pinned commit and then ships the literal
placeholder `<PINNED_COMMIT>`, so no commit was recorded. We take upstream `main`.
""")

code("""
LEWM = CODE / 'third_party' / 'lewm'
if LEWM.exists():
    print("already present:", LEWM)
else:
    !mkdir -p "{CODE}/third_party"
    !git clone --depth 1 https://github.com/lucas-maes/le-wm.git "{LEWM}"

if LEWM.exists():
    !git -C "{LEWM}" log -1 --oneline
else:
    print("clone failed — fine for this session; only the flat baseline needs it")
""")

# ------------------------------------------------- 5. env, helpers, guards -----

md("""
## 5. Environment, shell helper, two guards

`STABLEWM_HOME` holds the dataset, the staged checkpoints and the outputs, on
**Colab local disk** rather than Drive: the dataset is an HDF5 file read with random
access during evaluation, and Drive is far too slow for that. The cost is that it is
wiped when the session ends, which is what step 17 is for.

Two guards run here, both for mistakes this project actually made:

- **Mismatch 3.** `@hydra.main(config_path="../config/eval")` on a packaged module
  resolves to the *module* `h_le_wm.config.eval`, and the artifact ships those
  config directories without `__init__.py` although every other subpackage under
  `h_le_wm/` has one. Recent hydra-core then refuses with `Primary config module
  'h_le_wm.config.eval' not found`. Four empty files fix it — additive, idempotent,
  and the only change this project makes inside `code/`.
- **A stale Drive copy of `analysis/`.** Mismatches 6, 7 and 8 are fixed in
  `analysis/run_eval.py` and `analysis/hilewm_local/patches.py`. With an older copy
  the eval fails deep in the run, in a way that looks like the library's fault.
  Checking three function names costs a second.
""")

code("""
import os, subprocess, sys, threading, time
from pathlib import Path

STABLEWM_HOME = Path('/content/stablewm')
STABLEWM_HOME.mkdir(parents=True, exist_ok=True)

os.environ['STABLEWM_HOME'] = str(STABLEWM_HOME)
os.environ['PYTHONPATH'] = f"{CODE}:{ANALYSIS}:" + os.environ.get('PYTHONPATH', '')
os.environ['HILEWM_PATCH_CEM'] = '1'     # sitecustomize applies the CEM fix in subprocesses

for p in (str(ANALYSIS), str(CODE)):
    if p not in sys.path:
        sys.path.insert(0, p)

LAST_STDOUT = ''


def sh(cmd, cwd=CODE, check=False):
    # Run a shell command from code/ with the env above, streaming and capturing.
    global LAST_STDOUT
    print(f"$ {cmd}\\n", flush=True)
    lines = []
    proc = subprocess.Popen(cmd, shell=True, cwd=str(cwd), env=os.environ,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1, executable='/bin/bash')
    for line in proc.stdout:
        print(line, end='')
        lines.append(line)
    proc.wait()
    LAST_STDOUT = ''.join(lines)
    print(f"\\n[exit {proc.returncode}]", flush=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {cmd}")
    return proc.returncode


def gpu_mib(query):
    # Returns a string, '?' when nvidia-smi is unavailable or silent. Callers run in
    # a background thread, where an uncaught FileNotFoundError would print a
    # traceback in the middle of an evaluation.
    try:
        out = subprocess.run(['nvidia-smi', f'--query-gpu={query}',
                              '--format=csv,noheader,nounits'],
                             capture_output=True, text=True).stdout.strip()
    except (FileNotFoundError, OSError):
        return '?'
    return out.splitlines()[0] if out else '?'


def timed_run(cmd):
    # -> (exit code, wall seconds, peak GPU MiB). The eval runs in a subprocess, so
    # this kernel's allocator stats say nothing about it; poll nvidia-smi instead.
    peak = {'mib': 0}
    stop = threading.Event()

    def watch():
        while not stop.is_set():
            try:
                peak['mib'] = max(peak['mib'], int(gpu_mib('memory.used')))
            except ValueError:
                pass
            stop.wait(3.0)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    t0 = time.time()
    rc = sh(cmd)
    dt = time.time() - t0
    stop.set()
    watcher.join(timeout=5)
    return rc, dt, peak['mib']


# Guard 1 - mismatch 3: make the config directories importable packages.
for d in ('config', 'config/eval', 'config/train', 'config/train/data'):
    init = CODE / 'h_le_wm' / d / '__init__.py'
    if not init.exists():
        init.touch()
        print("created", init)

# Guard 2: does Drive's analysis/ carry fixes 6, 7 and 8?
import hilewm_local.patches as patches

stale = [n for n in ('apply_cem_env_count_fix', 'register_object_ckpt_aliases',
                     'apply_world_evaluate_alias') if not hasattr(patches, n)]
if 'apply_world_evaluate_alias' not in (ANALYSIS / 'run_eval.py').read_text():
    stale.append('run_eval.py does not apply the World alias')
assert not stale, (
    "Drive's analysis/ is out of date: " + ", ".join(stale) + ". Upload the current "
    "analysis/run_eval.py and analysis/hilewm_local/patches.py from the repo, then "
    "rerun this cell.")

print()
print("STABLEWM_HOME =", os.environ['STABLEWM_HOME'])
print("PYTHONPATH    =", os.environ['PYTHONPATH'])
print("GPU           =", gpu_mib('memory.total'), "MiB total")
print("analysis/ in Drive carries all three runtime fixes. Good.")
""")

# --------------------------------------------------------------- 6. dataset ----

md("""
## 6. Download the dataset

PushT only, from `quentinll/lewm-pusht`: one file, `pusht_expert_train.h5.zst`,
**13.1 GB compressed -> 46.3 GB extracted** (exact, from the zstd frame header).
`setup_datasets.sh` extracts with `zstd -d --rm`, so the compressed file is removed
as it goes and the peak is ~59 GB.

We deliberately do **not** call `setup_paper_datasets.sh`: it always pulls Cube as
well and refuses a `--datasets` argument. Cube is 46 GB compressed with no content
size in its header — certainly over 100 GB extracted. It will not fit, and we hold
no Cube checkpoints anyway.

This is the slow step: 45-55 minutes. The cell skips it when the file is already
there, so it is safe to rerun.
""")

code("""
import shutil

dataset_root = STABLEWM_HOME / 'pusht_expert_train.h5'
free = shutil.disk_usage('/content').free
print(f"free disk: {free/1e9:.1f} GB | dataset already present: {dataset_root.exists()}")

if dataset_root.exists():
    print(f"skipping the download ({dataset_root.stat().st_size/1e9:.1f} GB on disk)")
else:
    assert free > 62e9, ("not enough free disk for the 13.1 GB download plus the "
                         "46.3 GB extraction (~59 GB at peak)")
    sh(f'bash scripts/setup_datasets.sh --datasets pusht --home "{STABLEWM_HOME}"',
       check=True)

print("\\n--- HDF5 files under STABLEWM_HOME ---")
for f in sorted(STABLEWM_HOME.rglob('*.h5')):
    print(f"  {f.stat().st_size/1e9:8.1f} GB  {f.relative_to(STABLEWM_HOME)}")
print(f"\\nfree disk left: {shutil.disk_usage('/content').free/1e9:.1f} GB")
""")

# ---------------------------------------------------------- 7. dataset link ----

md("""
## 7. Link the dataset where the reader looks — mismatch 4

**This step is why a green preflight is not enough.** The HF repo keeps
`pusht_expert_train.h5.zst` at its root, so `setup_datasets.sh` writes
`$STABLEWM_HOME/pusht_expert_train.h5` — and `h_le_wm/validate.py:15` checks
exactly that path, so preflight passes. But the reader resolves a `datasets/`
subfolder: `HDF5Dataset.__init__` calls `get_cache_dir(cache_dir,
sub_folder='datasets')` (`stable_worldmodel/data/formats/hdf5.py:53`), i.e.
`$STABLEWM_HOME/datasets/pusht_expert_train.h5`.

Without the link the eval dies with `FileNotFoundError` — after the 45-minute
download. A hard link costs nothing and no second copy.
""")

code("""
dst_dir = STABLEWM_HOME / 'datasets'
dst_dir.mkdir(parents=True, exist_ok=True)
dataset_linked = dst_dir / 'pusht_expert_train.h5'

assert dataset_root.exists(), f"dataset missing: {dataset_root}  (did step 6 finish?)"
if not dataset_linked.exists():
    os.link(dataset_root, dataset_linked)        # hard link: same inode, no extra disk
print("linked:", dataset_linked)
print(f"  {dataset_linked.stat().st_size/1e9:.1f} GB | inode shared:",
      dataset_linked.stat().st_ino == dataset_root.stat().st_ino)

# Prove it opens, including the blosc-compressed pixels (mismatch 1).
import h5py
import hdf5plugin  # noqa: F401

with h5py.File(dataset_linked, 'r') as f:
    print("columns:", list(f.keys()))
    print("episodes:", len(f['ep_len']), "| rows:", f['action'].shape[0])
    print("pixels[0] reads:", f['pixels'][0].shape, f['pixels'][0].dtype)
""")

# --------------------------------------------------------- 8. flat baseline ----

md("""
## 8. Flat LeWM baseline — known broken, non-fatal, skippable

Not redistributed in the artifact; this downloads the Hub weights and converts
them. **It fails, and that is expected.** Upstream `main` and the released weights
disagree about the encoder:

| side | keys |
| --- | --- |
| model built from `third_party/lewm` | `encoder.layers.0.attention.q_proj.weight`, ... (its own ViT, logged as "Created ViT-tiny from scratch") |
| weights on the Hub | `encoder.encoder.layer.0.attention.attention.query.weight`, ... (HuggingFace `ViTModel`) |

That is the `<PINNED_COMMIT>` gap: no commit was ever recorded, so we clone `main`,
which has since replaced the HF encoder. `stable_worldmodel`'s own `LeWM` still
takes an injected encoder and calls it with `interpolate_pos_encoding=True`
(`wm/lewm/lewm.py:19,34`) — the HF API the weights were saved against — so the way
back is an older upstream commit, or building the baseline against a stock HF ViT in
`analysis/`. Neither is needed for **Hi-LeWM**, which is what this session measures.

**Do not pass `--allow-non-strict`, although the error message suggests it.** Every
encoder key is missing, so a non-strict load would leave the whole 12-layer pixel
encoder randomly initialised and save that as a baseline.

Consequence: the flat-vs-hierarchical comparison is deferred, and full preflight
cannot pass (step 10). Until then the paper's implied flat numbers (~52.7 at d=50,
~18.0 at d=75) are the reference.
""")

code("""
# check=False twice over: a rerun raises FileExistsError on existing targets, and
# the conversion itself fails on the encoder mismatch described above.
sh('bash scripts/setup_baseline_checkpoints.sh fetch-baselines')

baselines = {rel: (STABLEWM_HOME / rel).exists()
             for rel in ('pusht/lewm_object.ckpt', 'cube/lewm_object.ckpt')}
print()
for rel, ok in baselines.items():
    f = STABLEWM_HOME / rel
    print(f"  {'OK ' if ok else 'MISSING'}  {rel}"
          + (f"  {f.stat().st_size/1e6:.0f} MB" if ok else ""))

if not baselines['pusht/lewm_object.ckpt']:
    print("\\nNo flat baseline. Expected, and it changes nothing here:")
    print("  - the Hi-LeWM eval never touches it (only h_le_wm/baseline/* does)")
    print("  - full preflight in step 10 will fail on baseline integrity")
    print("  - the flat-vs-hierarchical comparison is deferred, not lost")
    print("  - do NOT rerun with --allow-non-strict (random pixel encoder)")
""")

# ------------------------------------------------------ 9. stage checkpoints ---

md("""
## 9. Stage the checkpoints, and link them where the loader looks — mismatch 5

`setup_checkpoints.sh` copies the files to the registry's relpaths under
`$STABLEWM_HOME`. Source paths come from step 2, so an unexpected Drive layout
already failed there. A rerun raises `FileExistsError` on targets that are already
staged, which is why this runs with `check=False` and asserts on the file instead.

Then the dataset problem again, one directory over: the registry stages into
`$STABLEWM_HOME/runs/...`, while `swm.policy.AutoCostModel` resolves a policy name
under `get_cache_dir(sub_folder='checkpoints')` and appends `_object.ckpt`
(`stable_worldmodel/policy.py:455-475`), i.e. `$STABLEWM_HOME/checkpoints/runs/...`.
Without the symlink the eval stops with `Checkpoint path does not exist: ... Launch
pretraining first.` One symlink covers every staged run, probes included.

(That function's first branch accepts `run_name` as a path when it exists, so an
absolute `policy=` would also work — but then the command stops matching the
authors' own matrix command, which is what keeps the number comparable.)

Two corrections to the artifact's own instructions: our `checkpoints.zip` has **no
Cube checkpoints** (76 files, all under `checkpoints/pusht/`), so the README's
`hierarchical/cube/default_epoch15` argument is dropped; and the registry has **no
entries for the VQ or fixed-stride variants**, which the later comparisons need.
""")

code("""
sh(f'''bash scripts/setup_checkpoints.sh \\\\
  --checkpoint hierarchical/pusht/default_epoch15="{CKPT_HI}" \\\\
  --checkpoint probe/pusht/phase_a="{CKPT_PROBE_A}" \\\\
  --checkpoint probe/pusht/phase_b="{CKPT_PROBE_B}"''')

POLICY = 'runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15'
staged = STABLEWM_HOME / (POLICY + '_object.ckpt')
print("\\nstaged:", staged.exists(), staged)
assert staged.exists(), "staging did not produce the checkpoint the eval loads"

ckpt_root = STABLEWM_HOME / 'checkpoints'
ckpt_root.mkdir(parents=True, exist_ok=True)
runs_link = ckpt_root / 'runs'
if not runs_link.exists():
    runs_link.symlink_to(STABLEWM_HOME / 'runs', target_is_directory=True)

resolved_by_swm = ckpt_root / (POLICY + '_object.ckpt')
print("swm will load:", resolved_by_swm, "->", resolved_by_swm.exists())
assert resolved_by_swm.exists(), "the checkpoints/runs symlink did not resolve"
""")

# ------------------------------------------------------------- 10. checks ------

md("""
## 10. Checks

Only the dataset check is usable as shipped. **`validate checkpoints --checkpoint
<name>` is not targeted**: `--tier` defaults to `required-now` and cannot be
switched off (argparse `choices` forbid an empty value), and
`iter_registry_entries` returns the **union** of the tier's entries and the named
ones (`h_le_wm/checkpoints.py:114-127`), so naming the Hi-LeWM checkpoint still
demands both flat baselines. With the baseline conversion broken, no invocation of
the shipped validator can pass on a PushT-only setup — so we check the one file the
eval actually loads.

Full preflight runs last, for information. It **will** fail while the baselines are
missing.
""")

code("""
sh('python -m h_le_wm.validate datasets --datasets pusht', check=True)

assert staged.is_file(), f"staged checkpoint missing: {staged}  (rerun step 9)"
print(f"[ok] {staged}  {staged.stat().st_size/1e6:.0f} MB")

rc = sh('bash scripts/validate_preflight.sh --datasets pusht')
print("\\nfull preflight:", "ok" if rc == 0
      else "failed — expected while the flat baselines are missing; the two checks "
           "above are the ones that matter")
""")

# --------------------------------------------------- 11. the runtime fixes -----

md("""
## 11. The three runtime fixes, and what they are for

`analysis/run_eval.py` is a thin wrapper: it applies these and then calls the
artifact's own `run()`, so the evaluation itself is unmodified code. Each fix is a
no-op when the installed library already behaves correctly.

**Mismatch 6 — `CEMSolver` derives the environment count from a string.**

```python
total_envs = len(next(iter(info_dict.values())))   # solver/cem.py:131
```

The artifact puts the string `planner_level` first
(`h_le_wm/planning/policies.py:793`, `:840`, `:954`), so the high level plans for
`len("high") == 4` envs and the low level for `len("low") == 3`. **No value of
`eval.num_eval` satisfies both**, verified on 2026-09-19 against the real
`HierarchicalWorldModelPolicy`: 1, 4, 8 and 50 all fail (4 passes `_plan_high` by
coincidence and then fails `_plan_low`). The line is byte-identical in 0.1.0 and
0.1.1. Their `EmpiricalMacroActionSolver` is correct, so only the plain-CEM path is
affected — Hi-LeWM-C would run unpatched. The fix reorders the info dict so a tensor
comes first, leaving the solver's arithmetic untouched.

**Mismatch 7 — the eval never registers the pickle aliases.** The released
checkpoints name the old `hi_train` modules (`hi_jepa`, `hi_module`, `hi_vq`,
`hi_waypoint_sampling`, `module`). `h_le_wm/train/hierarchical.py:41-54` maps all
five onto `h_le_wm.models.*`; `h_le_wm/eval/hierarchical.py:34-39` keeps only the
`_baseline_lewm_module` half of that block. So the shipped eval cannot load the
shipped checkpoints: `ModuleNotFoundError: No module named 'hi_jepa'`. This one is
internal to the artifact, and it means no run of `h_le_wm.eval.hierarchical` against
`pusht_hi_lewm_epoch15_object.ckpt` was possible as published.

**Mismatch 8 — `World.evaluate_from_dataset` does not exist.**
`h_le_wm/eval/hierarchical.py:562` calls it; 0.1.1 exposes the same behaviour as
`World.evaluate(dataset=..., ...)`, with `goal_offset_steps` renamed to
`goal_offset` and `video_path` to `video` (`world/world.py:188-255`, `:492`). The
alias is a thin forwarder.
""")

code("""
import importlib.metadata as meta

from hilewm_local.patches import (apply_cem_env_count_fix, apply_world_evaluate_alias,
                                  is_cem_env_count_fix_needed,
                                  register_object_ckpt_aliases)

print("stable-worldmodel:", meta.version("stable-worldmodel"))
print("CEM env-count fix needed:", is_cem_env_count_fix_needed())
print("CEM env-count fix applied in this kernel:", apply_cem_env_count_fix())
print("pickle aliases:", register_object_ckpt_aliases())
print("World.evaluate_from_dataset alias installed:", apply_world_evaluate_alias())
print()
print("HILEWM_PATCH_CEM:", os.environ.get('HILEWM_PATCH_CEM'),
      "(sitecustomize applies the CEM fix in subprocesses too)")
print("run_eval.py applies all three at the top of every run.")
""")

# ------------------------------------------------------- 12. sanity load -------

md("""
## 12. Sanity check: load the checkpoint by hand

With the aliases registered by the previous cell, `torch.load` works. Expect
`HiJEPA`, ~30.5M parameters (the paper's figure) and all five module groups: the
frozen low level (`encoder`, `action_encoder`, `low_predictor`) plus the two
trainable high-level modules.
""")

code("""
import torch

model = torch.load(CKPT_HI, map_location='cpu', weights_only=False)
print(type(model).__name__)
print(f"total params: {sum(p.numel() for p in model.parameters())/1e6:.1f}M  (paper: 30.5M)")

have = {k.split('.')[0] for k, _ in model.named_parameters()}
for expected in ('encoder', 'action_encoder', 'low_predictor',
                 'high_predictor', 'latent_action_encoder'):
    print(f"  {'OK ' if expected in have else 'MISSING'}  {expected}")
del model
""")

# ------------------------------------------------------- 13. eval command ------

md("""
## 13. Build the eval command

Every flag comes from `build_hierarchical_matrix_command`
(`h_le_wm/experiments/run.py:313-360`) and one row of
`h_le_wm/experiments/matrix/pusht/hierarchical_matrix.csv` — the authors' own d=50
online cell:

```
D50;;100;2;2;1;1;5;1;5;1500;40;10;900;30;150
```

The CEM budget comes from `hilewm_local.budgets.paper_budget`, our single source of
truth for paper Table 5 — written after we spent two days running d=50 with d=25's
iteration count.

**The shipped config is not the paper's**: `config/eval/hi_pusht.yaml` has high
900/20/topk 30 and low 600/30/topk 60. All six numbers are overridden. A run that
omits them is not comparable to 38.7.

**Mismatch 9.** The same config sets `world.history_size: 1` and
`world.frame_skip: 1`, which `swm.World` forwards to `gym.make`, and 0.1.1's
`PushT.__init__` accepts neither: `TypeError: unexpected keyword argument
'history_size'`. Version 0.1.1 has no frame stacking or skipping at all, so at 1 and
1 both keys are no-ops, and the command deletes them with Hydra's `~key` syntax
rather than translating them. All four `hi_*.yaml` eval configs carry those lines.

**`eval_budget` has a floor.** The eval asserts `eval_budget >= low_horizon *
low_action_block` (2 x 5 = 10) and `>= high_horizon * high_action_block`
(`h_le_wm/eval/hierarchical.py:478-491`), so the probes below use 10.

**One caveat on comparability:** the paper's 38.7 is the best configuration of a
sweep over these rows. We run the canonical row, so a single cell can land below
38.7 with nothing wrong, and at 50 episodes the standard error near 50 % is about
7 points.
""")

code("""
import re

from hilewm_local.budgets import paper_budget

RESULTS_ROOT = STABLEWM_HOME / 'our_evals'
PROBE_BUDGET = 10        # the smallest the eval accepts: low_horizon * action_block


def eval_cmd(*, goal_offset=50, num_eval=50, seed=42, mode='hierarchical',
             eval_budget=None, tag='run', extra=()):
    b = paper_budget(goal_offset)
    out_dir = RESULTS_ROOT / f"{tag}_d{goal_offset}_seed{seed}_n{num_eval}"
    args = [
        'python -u', str(ANALYSIS / 'run_eval.py'),
        '--config-name=hi_pusht',
        f'policy={POLICY}',
        f'seed={seed}',
        f'planning.mode={mode}',
        f'eval.num_eval={num_eval}',
        f'eval.goal_offset_steps={goal_offset}',
        # Mismatch 9. Quoted: bash would try tilde expansion on a bare ~word.
        "'~world.history_size'",
        "'~world.frame_skip'",
        f'eval.eval_budget={eval_budget if eval_budget is not None else b.eval_budget}',
        f'planning.high.solver.num_samples={b.high_samples}',
        f'planning.high.solver.n_steps={b.high_steps}',
        f'planning.high.solver.topk={b.high_topk}',
        f'planning.low.solver.num_samples={b.low_samples}',
        f'planning.low.solver.n_steps={b.low_steps}',
        f'planning.low.solver.topk={b.low_topk}',
        # matrix row D50: high h=2, low h=2, receding 1/1, replan 5, blocks 1/5
        'planning.high.plan_config.horizon=2',
        'planning.high.plan_config.receding_horizon=1',
        'planning.high.plan_config.action_block=1',
        'planning.high.replan_interval=5',
        'planning.low.plan_config.horizon=2',
        'planning.low.plan_config.receding_horizon=1',
        'planning.low.plan_config.action_block=5',
        'planning.high.solver.device=cuda',
        'planning.low.solver.device=cuda',
        'solver.device=cuda',
        f'output.filename=hi_pusht_d{goal_offset}_seed{seed}.txt',
        f'+output.root_dir={out_dir}',
        *extra,
    ]
    return ' '.join(args), out_dir


def parse_success_rate(stdout):
    # -> (rate, passed, failed). Two independent sources cross-check each other: the
    # metrics dict the library returns, and the per-episode lines the artifact
    # prints. Those lines must be deduplicated by eval_index, because the artifact
    # prints every outcome twice -- once under EPISODE OUTCOMES and again under
    # FAILED or PASSED EPISODES (eval/hierarchical.py:589-598). Counting raw lines
    # doubles the episode count and fails the gate on a perfectly good run.
    match = re.search(r"'success_rate':\\s*([0-9.]+)", stdout)
    rate = float(match.group(1)) if match else None
    status = {}
    for verdict, index in re.findall(r"^(PASS|FAIL)\\teval_index=(\\d+)", stdout,
                                    flags=re.M):
        status[int(index)] = verdict
    passed = sum(v == 'PASS' for v in status.values())
    failed = sum(v == 'FAIL' for v in status.values())
    return rate, passed, failed


probe_cmd, probe_out = eval_cmd(num_eval=4, eval_budget=PROBE_BUDGET, tag='probe')
print("the probe command, one argument per line:\\n")
for arg in probe_cmd.split(' '):
    print("   ", arg)
print("\\noutput ->", probe_out)
print("\\nTable 5 budget for d=50:", paper_budget(50))
""")

# ----------------------------------------------------------- 14. probe ---------

md("""
## 14. Wiring probe — 4 episodes, 10 steps

This resolves the whole pipeline: env, dataset, checkpoint, both CEM levels,
rollout, videos, manifest. It is the cheapest way to find that something is wrong,
and it is what caught six of the nine mismatches.

At 10 environment steps **no episode can succeed**, so the success rate it prints is
meaningless and must not be recorded. What to look for instead: `CEM solve time`
lines — the planner is alive — and `exit 0`.

For reference, the first session on an L4: high-level CEM 15.9 s and 16.0 s per
solve, low-level 7.4 s, one of each per 5 environment steps, 1.6 min in total, peak
GPU 409 MiB.
""")

code("""
rc, dt, peak_mib = timed_run(probe_cmd)

print(f"\\nprobe: {dt/60:.1f} min for 4 envs x {PROBE_BUDGET} steps")
print(f"peak GPU: {peak_mib} MiB of {gpu_mib('memory.total')} MiB")
print("exit:", rc)
assert rc == 0, ("the wiring is wrong, not the budget — read the traceback above. "
                 "The nine mismatches and where each is handled are listed in the "
                 "first cell.")
rate, passed, failed = parse_success_rate(LAST_STDOUT)
print(f"(printed success rate {rate}% over {passed + failed} episodes — meaningless "
      "at 10 steps, not recorded)")
""")

# ------------------------------------------------------- 15. scaling probe -----

md("""
## 15. Scaling probe — the same 10 steps at 50 envs

CEM cost scales with the **environment count**, and the real run uses 50 envs
against the probe's 4. Measuring 10 steps at 50 envs and multiplying by 10 is a far
better estimate than extrapolating across a 12.5x batch, and it costs a few minutes
instead of risking a two-hour surprise.

Memory is not expected to be the constraint: 4 envs peaked at 409 MiB of 15360.
""")

code("""
scale_cmd, scale_out = eval_cmd(num_eval=50, eval_budget=PROBE_BUDGET, tag='scale')
rc, dt, peak_mib = timed_run(scale_cmd)

print(f"\\n50 envs, {PROBE_BUDGET} steps: {dt/60:.1f} min | peak GPU {peak_mib} MiB "
      f"of {gpu_mib('memory.total')} MiB")
ESTIMATED_REAL_MIN = dt * 10 / 60
print(f"the real run does 100 steps, i.e. 10x the planning: roughly "
      f"{ESTIMATED_REAL_MIN:.0f} min plus a minute of setup")
print("exit:", rc, "| the success rate here is still meaningless at 10 steps")
if ESTIMATED_REAL_MIN > 90:
    print("\\nOver 90 min: prefer 2 x 25 episodes with different seeds in step 16 and "
          "pool them. Never cut the CEM budget instead.")
""")

# --------------------------------------------------------- 16. the real run ----

md("""
## 16. The real run — our first success rate

Hi-LeWM online, plain CEM, d=50, paper Table 5 budget, seed 42, 50 episodes.

If step 15 says this will not fit in the session, run it as `2 x 25` or `5 x 10`
with different seeds and pool the episodes — but **record the split**, because
`num_eval` *is* the episode count. Never cut the CEM budget instead: the budget is
what makes the number comparable to 38.7.

The cell parses the success rate out of the run, cross-checks it against the
per-episode PASS/FAIL lines (a different code path in the artifact), and appends a
`results/runs.csv` row straight to Drive, so the number cannot die with the session.

One quirk in the output paths: `output.subdir` is `null` and the artifact builds the
directory from it as a string, so files land under `<root_dir>/None/`.
""")

code("""
import datetime

NUM_EVAL, SEED, GOAL_OFFSET = 50, 42, 50      # edit for a split or another offset

real_cmd, real_out = eval_cmd(num_eval=NUM_EVAL, seed=SEED, goal_offset=GOAL_OFFSET,
                              tag='hi_online')
rc, dt, peak_mib = timed_run(real_cmd)
print(f"\\nwall clock: {dt/60:.1f} min | peak GPU {peak_mib} MiB | exit: {rc}")
assert rc == 0, "the run failed; nothing recorded"

rate, passed, failed = parse_success_rate(LAST_STDOUT)
print(f"\\nsuccess rate: {rate}%   ({passed} passed, {failed} failed, "
      f"{passed + failed} episodes)")
assert rate is not None, "could not parse the success rate from the run output"
assert passed + failed == NUM_EVAL, (
    f"episode lines ({passed + failed}) do not match num_eval ({NUM_EVAL})")
assert abs(rate - 100.0 * passed / NUM_EVAL) < 0.51, (
    f"the printed rate {rate}% disagrees with the episode lines ({passed}/{NUM_EVAL})")
print("gate passed: the metrics dict and the per-episode lines agree")
print("paper's d=50 online cell: 38.7 % (best of a sweep; ~7 points of standard "
      "error at 50 episodes)")

# The row goes to Drive immediately: local disk dies with the session.
rows_csv = ARTIFACT / 'results' / 'colab' / 'runs_rows.csv'
rows_csv.parent.mkdir(parents=True, exist_ok=True)
if not rows_csv.exists():
    rows_csv.write_text("date,git_commit,checkpoint,planner_variant,d,seed,"
                        "n_episodes,success_rate,config_path\\n")
commit = subprocess.run(['git', '-C', str(ARTIFACT), 'rev-parse', '--short', 'HEAD'],
                        capture_output=True, text=True).stdout.strip() or 'unknown'
row = (f"{datetime.date.today()},{commit},"
       "pusht/main/pusht_hi_lewm_epoch15_object.ckpt,hi_online_plain_cem,"
       f"{GOAL_OFFSET},{SEED},{NUM_EVAL},{rate},"
       "config/eval/hi_pusht.yaml+paper_table5_overrides\\n")
with rows_csv.open('a') as fh:
    fh.write(row)
print(f"\\nappended to {rows_csv}:\\n{row}")

print("--- result files ---")
for f in sorted(real_out.rglob('*')):
    if f.is_file():
        print(f"   {f.stat().st_size/1e6:7.1f} MB  {f.relative_to(real_out)}")
""")

# ------------------------------------------------------------ 17. save out -----

md("""
## 17. Copy everything to Drive before the session dies

`STABLEWM_HOME` is on local disk and is wiped when the session ends. The
`runs_rows.csv` row from step 16 is already on Drive; this copies the result files,
the episode manifests and the videos — the videos are the only direct view of what
the planner actually does, so they are worth keeping.
""")

code("""
DRIVE_OUT = ARTIFACT / 'results' / 'colab'
DRIVE_OUT.mkdir(parents=True, exist_ok=True)

total = 0
for src_dir in sorted(RESULTS_ROOT.glob('*')):
    if not src_dir.is_dir():
        continue
    dst = DRIVE_OUT / src_dir.name
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src_dir, dst)
    size = sum(f.stat().st_size for f in dst.rglob('*') if f.is_file())
    total += size
    print(f"  {size/1e6:8.1f} MB  -> {dst}")

repro = STABLEWM_HOME / 'repro'
if repro.exists():
    dst = DRIVE_OUT / 'repro'
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(repro, dst)
    print("  copied ->", dst)

print(f"\\n{total/1e6:.0f} MB on Drive under {DRIVE_OUT}")
print("\\nOn the laptop: fold results/colab/runs_rows.csv into results/runs.csv,")
print("update docs/STATUS.md, and commit.")
""")

# ----------------------------------------------------------- 18. appendix ------

md("""
## Appendix — resume after a runtime restart

A restart clears the kernel but **not** `/content`, so the dataset, the extracted
checkpoints and everything staged survive. Run this cell instead of steps 2-12, then
continue from step 13.
""")

code("""
from google.colab import drive
drive.mount('/content/drive')

import os, shutil, subprocess, sys, threading, time
from pathlib import Path

ARTIFACT = Path('/content/drive/MyDrive/inzva-final')
CODE = ARTIFACT / 'code'
ANALYSIS = ARTIFACT / 'analysis'
STABLEWM_HOME = Path('/content/stablewm')
LOCAL_CKPTS = Path('/content/ckpts')

os.environ['STABLEWM_HOME'] = str(STABLEWM_HOME)
os.environ['PYTHONPATH'] = f"{CODE}:{ANALYSIS}:" + os.environ.get('PYTHONPATH', '')
os.environ['HILEWM_PATCH_CEM'] = '1'
for p in (str(ANALYSIS), str(CODE)):
    if p not in sys.path:
        sys.path.insert(0, p)

CKPT_HI = next(p for p in (
    LOCAL_CKPTS / 'checkpoints/pusht/main/pusht_hi_lewm_epoch15_object.ckpt',
    ARTIFACT / 'checkpoints/pusht/main/pusht_hi_lewm_epoch15_object.ckpt')
    if p.is_file())
POLICY = 'runs/pusht_hierarchical_default/pusht_hierarchical_default_epoch_15'
staged = STABLEWM_HOME / (POLICY + '_object.ckpt')
dataset_root = STABLEWM_HOME / 'pusht_expert_train.h5'

for d in ('config', 'config/eval', 'config/train', 'config/train/data'):
    (CODE / 'h_le_wm' / d / '__init__.py').touch(exist_ok=True)

import transformers
import transformers.models.vit.modeling_vit as mv

print("transformers:", transformers.__version__,
      "| ViTEncoder present:", hasattr(mv, 'ViTEncoder'))
assert hasattr(mv, 'ViTEncoder'), "install transformers<5.9, then restart"

import hilewm_local.patches as patches

for name in ('apply_cem_env_count_fix', 'register_object_ckpt_aliases',
             'apply_world_evaluate_alias'):
    assert hasattr(patches, name), f"Drive's analysis/ is stale: {name} missing"

print("dataset linked:", (STABLEWM_HOME / 'datasets/pusht_expert_train.h5').exists(),
      "| staged ckpt:", staged.is_file(),
      "| swm path:", (STABLEWM_HOME / 'checkpoints' / (POLICY + '_object.ckpt')).is_file())
print("CKPT_HI:", CKPT_HI)
print()
print("Next: rerun the step 5 cell (sh / timed_run helpers), then step 13, then go on.")
""")

# ------------------------------------------------------------- 19. gotchas -----

md("""
## Gotchas

**Session limits.** Colab disconnects on idle, and `STABLEWM_HOME` dies with the
session — step 17 exists for that. On a new session steps 3 and 6 are the slow ones;
a restart inside a session needs only the appendix cell.

**Disk.** PushT is 46.3 GB extracted, ~59 GB at peak. Step 6 asserts on free space
and skips the download when the file is there.

**Never skip the two links (steps 7 and 9).** Preflight passes without the first and
the eval still fails, 45 minutes later.

**Keep `analysis/` in Drive current.** Three of the nine fixes live in
`analysis/run_eval.py` and `analysis/hilewm_local/patches.py`; step 5 refuses to
continue with an older copy.

**`run_pusht_smoke.sh` is not an eval of the released checkpoint.** Spec
`smoke/pusht` *trains* a one-epoch `pusht_smoke` model and evaluates that
(`h_le_wm/experiments/specs/smoke/pusht.yaml`). Steps 14-16 replace it.

**Do not run `run_pusht_hierarchical_matrix.sh`.** 23 rows x 50 episodes; at even 30
minutes a row that is 11+ hours and will not survive a session.

**Ask before long sweeps.** One run at a time, each row appended to
`results/runs.csv`.

**Most of the diagnosis needs no Colab at all.** `analysis/hilewm_local` rebuilds the
model from the `*_weights.ckpt` state dicts and runs the real `CEMSolver` on CPU —
see `analysis/README.md`. Colab is for what needs the environment: rollouts, success
rates, the acting diagnostics.

## Next, once step 16 produces a number

1. **d=75** at its Table 5 budget — `eval_cmd(goal_offset=75)` handles it
   (1200/60/10, low 1200/30/150, budget 150). The paper's clearest hierarchy win:
   32.7 for Hi-LeWM-C against 15.3 for plain CEM.
2. **Hi-LeWM-C online** — `extra=('planning.high.empirical_macro.enabled=true',)`.
   The comparison this project is built around, and the one planner path that runs
   without the CEM patch.
3. **Staged** — `mode='hierarchical_staged'`.
4. **VQ-16 / VQ-128** — no registry entries exist for them; stage the files under a
   new run name or add entries first.
5. **Seeds.** Everything we have is one seed family; >= 3 seeds is still an open gap,
   and at 50 episodes the standard error is ~7 points.
6. **The flat baseline**, which needs the upstream encoder question settled (step 8).
""")

# ----------------------------------------------------------------- build -------

nb = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "L4"},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

out = Path(__file__).resolve().parent / "colab_setup.ipynb"
out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")


def _stub_magics(text: str) -> str:
    return "\n".join(
        re.sub(r"^(\s*)[!%].*$", r"\g<1>pass", line) for line in text.split("\n")
    )


def _binds(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names


problems: list[str] = []
defined: set[str] = set()
written = json.loads(out.read_text())["cells"]

for index, cell in enumerate(written):
    source = cell["source"]
    if any(not line.endswith("\n") for line in source[:-1]):
        problems.append(f"cell {index}: source line without a trailing newline")
    if cell["cell_type"] != "code":
        continue
    text = _stub_magics("".join(source))
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        problems.append(f"cell {index}: {exc}")
        continue
    here = _binds(tree)
    used = {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    unknown = sorted(
        name for name in used
        if name not in here and name not in defined and not hasattr(builtins, name)
    )
    if unknown:
        problems.append(f"cell {index}: used before assignment: {unknown}")
    defined |= here

if problems:
    print(f"FAILED: {out}", file=sys.stderr)
    for problem in problems:
        print("  ", problem, file=sys.stderr)
    raise SystemExit(1)

print(f"wrote {out} ({len(cells)} cells, "
      f"{sum(1 for c in written if c['cell_type'] == 'code')} code, validated)")
