# Where everything is

One map of every document in this repository. The project, hierarchical planning
with latent world models on PushT, has two parts: we build our own coarse-to-fine
planner, and we diagnose the published hierarchical planner (Hi-LeWM). They share
the PushT dataset and nothing else: different code, environments and goal
offsets, so **their success rates are never compared**.

## Part 1: coarse-to-fine planning with a GRU world model

d=25, horizon 10, seeds 0-2. Lives at the repository root.

| if you want | read |
| --- | --- |
| what the project tests and why | `notes/inzva-report-4.html`, the spec as sent before presentation 4. **Frozen, never edited**: its 40-step horizon and stride 8 are out of date (manual §13) |
| where we are, what we decided, what is left | `notes/inzva-progress.html`, the status page. Ships in the same commit as the work it describes (team rule 5) |
| how to run anything, and why each setting is what it is | `INZVA_README.md`, the manual. Code and configs cite it by section number |
| a number someone quoted | `notes/results/<run>_results.md`, one per run, written by `scripts/collect_results.py`; never edited by hand |

## Part 2: the Hi-LeWM subgoal diagnosis

d=50, the paper's released checkpoints, seed 42. Lives in `hilewm/`.

| if you want | read |
| --- | --- |
| what it is, and setup | `hilewm/README.md` |
| where it stands | `hilewm/docs/STATUS.md` |
| every measurement, with corrections | `hilewm/docs/FINDINGS.md` |
| which numbers survived the lost working tree | `hilewm/docs/RECONSTRUCTION.md`. Read before quoting anything |
| how to run the analysis | `hilewm/analysis/README.md` |
| how to run evals on Colab | `hilewm/docs/COLAB_PLAN.md` |
| the records behind every number | `hilewm/results/README.md` |
| the paper, the plan and the working rules | `hilewm/CLAUDE.md` |
| the authors' artifact notes | `hilewm/docs/ARTIFACT_README.md`, `hilewm/code/README.md`, `hilewm/checkpoints/README.md` |

## Presentations

| path | what |
| --- | --- |
| `presentation/` | the final deck, and a map of each headline number to its record |
| `presentation/previous/presentation-3.pptx` | presentation 3 |

## Not ours

`README.md` and `docs/` are upstream stable-worldmodel's own README and
documentation site, unchanged.
