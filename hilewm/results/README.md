# results/

Every number in `docs/FINDINGS.md` should trace to a file here. **Rewritten
2026-10-05**; the original was lost, and so were most of the records it
described. What came back, and how, is in `docs/RECONSTRUCTION.md`.

## Two tables

| file | what goes in it | written by |
| --- | --- | --- |
| `runs.csv` | **evaluation runs**: success rates from real rollouts. One row per run, the schema `CLAUDE.md` prescribes plus a `source` column | `analysis/rebuild_runs_csv.py`, from the Colab records below |
| `measurements.csv` | **diagnostic measurements**: one row per local record, pointing at its JSON | `hilewm_local/results.py`, automatically |

They are separate on purpose: a diagnostic is not an evaluation.

## Records

`<script>/<timestamp>[_<tag>].json`, one per run, written by
`hilewm_local.results.recorded_run`. Each holds the commit at start and end,
whether `analysis/` or `code/` was dirty, the exact command line, every
argument, the structured metrics, and the full printed output. To re-run a
record, read its `argv`.

Records dated **2026-10-05** were regenerated in this repository after the
originals were lost. They are not copies; they are new runs, and their
`git_commit` is a commit of this repository.

## Colab outputs

`colab/` holds what came off the GPU and is irreplaceable, since none of it can
be regenerated without a Colab session:

| path | contents |
| --- | --- |
| `colab/runs_rows.csv` | the row each eval appended to Drive as it finished |
| `colab/manifests/*_episodes.tsv` | per-episode outcomes, which pairing needs. Eval runs and acting runs use the same format |
| `colab/acting/*.json`, `*.npz`, `*.tsv` | the acting diagnostics: summaries, per-episode arrays, appended tables |
| `colab/<run>/None/env_*.mp4` | episode videos. `None/` is the artifact's `output.subdir: null`, rendered as a string |

The Hydra config and log of every eval run are in `../code/outputs/`.

## Regenerating

```bash
cd hilewm
python analysis/rebuild_runs_csv.py --check     # is runs.csv current?
python analysis/summarize_eval_runs.py          # intervals for every run
python analysis/compare_eval_runs.py A.tsv B.tsv --tag name
```

Anything that reaches a slide must come from a script and leave a record here,
never from a terminal snippet.
