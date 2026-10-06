# Hi-LeWM subgoal diagnosis

Why does hierarchical planning in LeWorldModel pick bad subgoals? This project
takes the released checkpoints of *"Mind the Gap: Promises and Pitfalls of
Hierarchical Planning in LeWorldModel"* (Caselli et al., arXiv 2607.12547) and
measures, rather than restates, the paper's explanation. It trains nothing.

It is the inzva team's second project, separate from the coarse-to-fine solver
at the root of this repository. The two share the PushT dataset and the
`stable-worldmodel` library, but not code, environments or goal offsets (this
one uses d=50; the root project uses 25), so **their success rates are not
comparable**.

## Reading order

| if you want | read |
| --- | --- |
| where it stands, in five minutes | `docs/STATUS.md` |
| every measurement, with its caveats and corrections | `docs/FINDINGS.md` |
| **which numbers to trust after the files were lost** | `docs/RECONSTRUCTION.md` |
| how to run the analysis | `analysis/README.md` |
| how to run evals on Colab | `docs/COLAB_PLAN.md` |
| the paper, the plan and the working rules | `CLAUDE.md` |
| the authors' own archive notes | `docs/ARTIFACT_README.md` (its paths are relative to `hilewm/`), `code/README.md`, `checkpoints/README.md` |

## Layout

```text
analysis/     our code; imports the artifact, never edits it
code/         the authors' artifact, as released (four empty __init__.py added)
checkpoints/  configs in git; weights here on the machine that ran it (gitignored)
results/      every measurement, plus the irreplaceable Colab outputs
docs/         STATUS, FINDINGS, the Colab plan, the reconstruction ledger, the authors' README
```

## Setup on this machine (Windows, CPU)

The analysis runs on CPU in its own environment, never the root project's: it
needs `stable-worldmodel` **0.1.1**, the root project pins its own fork.

```bash
cd hilewm
uv venv .venv --python 3.11
uv pip install --python .venv/Scripts/python.exe "torch==2.11.*" torchvision \
    --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv/Scripts/python.exe einops "transformers<5.9" h5py \
    hdf5plugin numpy scipy scikit-learn pyyaml omegaconf pillow matplotlib gymnasium loguru

# put code/ and analysis/ on the path (PYTHONPATH breaks on the spaces in this path)
SP=$(.venv/Scripts/python -c "import site; print(site.getsitepackages()[-1])")
printf '%s\n%s\n' "$(cygpath -w "$PWD/code")" "$(cygpath -w "$PWD/analysis")" > "$SP/hilewm_paths.pth"

# the weights, 3.7 GB extracted: already in checkpoints/ on the machine that ran the
# reconstruction (verified against the original zip's CRCs). Anywhere else, download
# checkpoints/ from the authors' Zenodo artifact (doi:10.5281/zenodo.21353240) and
# unpack it here; this project never uses its cube/ part.
```

Then, from `hilewm/`:

```bash
export PYTHONUTF8=1      # the scripts print ẑ, ², —; Windows' console codec cannot
.venv/Scripts/python analysis/audit_dimensionality.py \
    --dataset ../.stable-wm/datasets/pusht_expert_train.h5 --checks draws --variants d32
```

The dataset is the root project's copy (`INZVA_README.md` §5), byte-identical to
the one this project was measured on. The first run downloads the
`stable-worldmodel` 0.1.1 wheel into `analysis/.cache/` and extracts it; nothing
is installed.

Linux and macOS: the same, with `bin/` for `Scripts/` and
`export PYTHONPATH="$PWD/code:$PWD/analysis"` instead of the `.pth` file.

Evaluations and acting diagnostics need the environment and a GPU, and run on
Colab: `docs/COLAB_PLAN.md`.

## The upstream LeWM source

Not redistributed; fetch it into `code/third_party/lewm` when a baseline path
needs it (`code/THIRD_PARTY_LEWM.md`). The commit this project used is
`8edfeb336732b5f3ce7b8b210d0ba370a09e2cac`.
