Hi-LeWM reuses the LeWorldModel baseline implementation for:

- the frozen low-level LeWM components used by Hi-LeWM;
- baseline checkpoint conversion and evaluation helpers;
- baseline-owned configuration files referenced by compatibility wrappers.

The local code expects the upstream checkout at:

```text
code/third_party/lewm
```

## How To Fetch It

From inside `code/`, run:

```bash
mkdir -p third_party
git clone https://github.com/lucas-maes/le-wm.git third_party/lewm
```

For exact archival reproducibility, replace `<PINNED_COMMIT>` with the commit
used for the released artifact:

```bash
git -C third_party/lewm checkout <PINNED_COMMIT>
```

If no exact commit is provided, use the upstream repository version compatible
with the `stable-worldmodel` release installed by `environment-gpu.yml`.

## Why It Is Not Included

The upstream LeWorldModel implementation is not authored by this artifact's
authors. Readers should consult the upstream repository for its license,
copyright, citation, and maintenance history.

The paper cites:

```text
LeWorldModel: Stable End-to-End Joint-Embedding Predictive Architecture from Pixels
Lucas Maes, Quentin Le Lidec, Damien Scieur, Yann LeCun, Randall Balestriero
arXiv:2603.19312
```

## Validation Note

Baseline-dependent commands require this checkout. If `third_party/lewm` is
missing, commands such as the baseline integrity check, baseline evaluation, and
some checkpoint conversion paths will fail with a message pointing to the
missing directory.
