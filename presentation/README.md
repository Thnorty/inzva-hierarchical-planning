# presentation/

The final showcase deck goes here as a self-contained HTML page, alongside the
decks that came before it.

| path | what it is |
| --- | --- |
| `index.html` | **the deck**: 17 slides, 11:25. The project for a general audience, in the inzva house structure — agenda, team, problem, literature review, dataset, pipeline, methods, results, demo, future directions, thank you |
| `sunum.html` | **the Turkish deck**: 20 slides, 14:20. The final-presentation deck, rebuilt from `Hi-LeWM Final Sunumu.pptx` in this folder's design system. Turkish throughout, technical terms in English. The speech script (`Hi-LeWM Final Sunumu Konuşma Metni.txt`) is numbered to match it slide for slide |
| `assets/sunum/` | what `sunum.html` needs: the PushT gif, the two data figures lifted from the pptx, and the three hierarchy-chain frames cropped out of its example figure |
| `assets/inzva.webp` | the inzva wordmark, shown in the top-right corner of every `sunum.html` slide. White artwork on transparency, inverted in CSS on the light slides — see below |
| `assets/pusht-wall.gif`, `assets/pusht-episode.gif` | real episodes of our planner, made by `make_gifs.py` from the Experiment A sweep's videos (600 samples, seed 4, successful episodes only; run it with `--videos` and `--results` pointing into `$STABLEWM_HOME/checkpoints/`) |
| `assets/team/` | **put `defne.jpg`, `oguz.jpg` and `arda.jpg` here**, square crops work best. Until then the deck shows initials |
| `assets/subgoal-strip.png` | the decoded-waypoint figure, made by `make_subgoal_strip.py` from hilewm's own 16-row panel |
| `previous/presentation-3.pptx` | presentation 3, as given ("Proj Presentation #3"): Push-T, VLA vs world models, the GRU predictor, CEM, MPC, temporal hierarchy |
| `../notes/inzva-report-4.html` | the spec sent before presentation 4. Frozen, never edited; its 40-step horizon and stride 8 are out of date (`INZVA_README.md` §13) |

### Light and dark

The deck carries both palettes: `:root` is the light one, and the dark one
comes from `@media (prefers-color-scheme: dark)` behind a
`:root:not([data-theme="light"])` guard. `index.html` is **pinned light**, by
`data-theme="light"` on its `<html>` tag, because it is shown on projectors and
printed to PDF, where following the machine running it is wrong. It is an
attribute rather than a script so that it holds before the first paint and with
JavaScript off. Delete it and the deck follows the machine again; set it to
`"dark"` to pin it the other way. There used to be a generated
`index-light.html` for this, written by a `make_light.py`; both are gone,
because one attribute does the same job.

A caveat worth knowing before judging the result: a browser dark-mode
extension will re-darken a light page, and it does so unevenly — inline SVG
fills survive while the page background does not. If the deck looks half dark,
check the extension before changing the CSS.

There was briefly a second, shorter deck and a third with the statistics on the
slides. Both are gone: one deck is easier to keep true than three. The numbers
they carried are not lost — the intervals, p-values and per-seed counts live in
`notes/results/` and `hilewm/results/`, and the table below says which file
holds which. Recover either deck from git history if a question ever needs it.

## Presenting

Open `index.html` in a browser, from this folder so it finds `assets/`. GIFs
play and loop on their own. It needs the internet only for its two fonts, and
falls back to Georgia and Consolas without it.

| key | does |
| --- | --- |
| → , space, Page Down | next slide (a presenter clicker sends these) |
| ← , Page Up | previous slide |
| N | speaker notes, with each slide's time budget and a running clock |
| F | full screen |

The timer starts on the first move. The budgets add up to 11:25:

| slide | seconds | | slide | seconds |
| --- | --- | --- | --- | --- |
| 1 title | 30 | | 10 our idea, two time scales | 50 |
| 2 agenda | 20 | | 11 Experiment A, budget sweep | 60 |
| 3 who we are | 20 | | 12 a published planner | 50 |
| 4 the task | 40 | | 13 why its waypoints are wrong | 60 |
| 5 why not a VLA | 60 | | 14 demo | 40 |
| 6 what we built on | 35 | | 15 same lesson twice | 30 |
| 7 the data | 30 | | 16 where we go next | 35 |
| 8 world models | 50 | | 17 to sum up | 30 |
| 9 the model | 45 | | | |

**If the slot is eight minutes**, drop the six sections added for the house
structure — 2 (agenda), 6 (literature review), 7 (the data), 9 (the model),
14 (demo) and 16 (where we go next). They total 3:25, so the deck lands on
exactly 8:00, which is what it ran at before they were added.

To lose less, cut only 2, 6, 7 and 16, which carry no result between them: that
is 2:00 and leaves **9:25**, keeping the model slide and the demo. Say their
content while slides 4 and 11 are up.

`index.html#6` opens on slide 6.

## The Turkish deck (`sunum.html`)

The final presentation, rebuilt from `Hi-LeWM Final Sunumu.pptx` so that the
deck and the speech script agree. It uses this folder's design system — same
palette, same 1600x900 stage. Open it from this folder so it finds `assets/`.

**It has no speaker-notes panel and no rehearsal clock**, unlike `index.html`:
the script is the notes, read from its own file. So `N` does nothing here, and
the keys are → / space / Page Down, ← / Page Up, Home, End and `F` for full
screen. The controls are a bare `←  n / 20  →` in the bottom-left corner that
fades out after a few seconds of no mouse movement; its 4px inset is as large
as it goes before the arrow overlaps the footer's source line. Across the top
is one progress segment per slide, filling as you advance.

Unlike `index.html` it is **always light**, whatever the machine is set to:
there is no `prefers-color-scheme` rule in it, so it needs no `data-theme` pin
at all. Two slides are deliberately dark, the stage-2
question (12) and the closing *Sorular?* (20); they carry `class="slide dark"`,
which redefines the palette variables on the section itself. Add or remove that
class to change which slides invert — nothing else needs touching.

**The inzva wordmark** sits in the top-right corner of all 20 slides, on the
eyebrow line. It is a single `<img class="brand">` at the end of `.stage`, not
a copy per slide: only one slide is visible at a time, so one element is enough
and slides stay free of boilerplate. `assets/inzva.webp` is white artwork on a
transparent background, so it would vanish on the eighteen light slides as it
stands. The CSS turns it black there with `filter:invert(1)` and leaves it
white on the two dark ones; `opacity:.33` is what makes it read as a watermark
rather than a second headline, and it lands on the same grey either way. Which
of the two applies is decided by `.dark-page`, the class the navigation code
puts on `<html>` whenever a dark slide is showing — the same mechanism the
bottom control bar uses. To move or resize it, edit `.brand`'s `top` / `right`
/ `height`.

Do not be tempted to recolour it with a CSS `mask` instead, which looks like
the tidier trick: `mask-image` fetches under CORS rules, and on a page opened
as `file://` — which is how this deck is usually opened — it fails silently and
the mark never appears at all. An `<img>` has no such restriction.

It is a different deck from `index.html`, not a translation of one: 20 slides
following the pptx's own order, where `index.html` has 17 in the house
structure. Both are true; they are cut for different audiences.

Three conventions worth knowing before editing it:

- **Language.** Turkish throughout, technical terms in English, which is the
  rule the speech script sets. Where the pptx had a Turkish gloss and the
  script had the English term, the script wins — so the deck says `subgoal`
  (not *ara hedef*), `high-level` / `low-level` (not *üst/alt seviye*),
  `episode`, `frame`, `action`, `reward`, `expert`, `score`, `draw`,
  `threshold`, `planner`. Keep it that way; a gloss here desyncs the script.
- **Corner numbers.** Every slide is numbered, 1 to 20, matching the deck
  position — the cover is 1 and the team slide 2, where the pptx left both
  blank and numbered the rest 1 to 18. So a slide's corner number is now its
  pptx number plus two, and `sunum.html#5` is the slide that says 5. The number
  comes from `data-no` on each `<section>`, kept explicit so the pptx's
  numbering can be restored in one place if it is ever wanted.
- **Figures.** The schematics are inline SVG, drawn in the deck's palette, so
  they follow light and dark like everything else. Only the three real-data
  figures are images. The pptx had the two-time-scales figure as a screenshot
  of `index.html`'s English one; `sunum.html` redraws it in Turkish.

The budgets are the script's and add up to **14:20**: its old 15:05, minus the
two slides since cut from the pptx (*İki örnek: Episode 9* and the unnumbered
*Episode 27*), plus the 15 seconds slide 4 gained when Ha & Schmidhuber's 2018
*World Models* was added to the literature list. The script has been renumbered 1 to 20 to match the
corners, those two sections dropped, and its section table, time total and
cross-references updated with it. Keep the two in step: a slide added or moved
here needs the same change there.

Each `<section>` still carries its budget as `data-time` in seconds, but with
the clock gone nothing reads it any more. It is kept as a record of the plan,
and as what a timer would read from if one is ever wanted back.

The two findings are labelled: slide 14 is *Bulgu 1* (the planner fools the
model) and slide 17 is *Bulgu 2* (failures come from two levels). They are the
same two conclusions the *Sonuçlar* slide numbers 1 and 2. The pptx had only a
*Bulgu 1*, with nothing answering it.

Two things the deck inherits from the pptx and cannot fix here, because
nothing in this repo generates them:

- `assets/sunum/subgoal-gorselleri.png` was exported cropped — its title says
  four rows and the file holds two. `sunum.html` uses
  `subgoal-gorselleri-2satir.png`, the same file trimmed so the cut third row
  does not show. Re-export it to get all four back.
- That figure and `basarisizlik-haritasi.png` have their labels baked in, in
  the pptx's older wording (*ara hedef*, *bölüm*, *ajan*, *uzman*). The slide
  text around them uses the script's terms. Regenerating them is the only fix.

## The rule for slides

Every number on a slide comes from a record, never from memory or a terminal
snippet. The project's two parts keep their records in different places and
use different goal offsets (d=25 for our planner, d=50 for Hi-LeWM), so **their
success rates never share an axis**.

The slides themselves no longer print those paths. The footers used to carry
them and now carry a plain line for the audience, or nothing, so **this file is
the only map** from a number on a slide to the record behind it. Keep the
tables below in step with the deck.

## Where each headline number lives

### Part 1: coarse-to-fine planning (`notes/`, `INZVA_README.md`)

Seeds 0, 1, 2; 50 episodes each; d=25, horizon 10.

| claim | number | record | context |
| --- | --- | --- | --- |
| Experiment A: success against budget, three planners | 25 to 600 samples, 5 seeds, 250 episodes per point | `notes/results/expA_sweep_results.md` | §14 |
| coarse beats flat at equal compute | +12.0 at 15,000 evaluations (p = 0.0003), +9.6 at 7,500 (p = 0.0007), +6.4 at 90,000 (p = 0.04) | `expA_sweep_results.md`, last three paired rows | §14 |
| refinement adds nothing | ours vs coarse alone: +2.4, 0.0, 0.0, -2.4, +0.4, none significant | `expA_sweep_results.md` | §14 |
| flat CEM on our GRU | 69.3 % | `notes/results/inzva_gru_results.md` | §14 |
| Experiment C, ours at k = 1 (the control) | 70.0 %, passed | `notes/results/expC_results.md` | §14 |
| coarse model alone | 76.0 % | `notes/results/inzva_gru_coarse_results.md` | §14 |
| ours at k = 2 | 76.0 % | `notes/results/inzva_gru_hier_results.md` | §14 |
| horizon 40 vs 10, before the replanning change | 15.3 % vs 64.0 % | `notes/results/gru_horizon40_results.md`; the 64.0 % is `inzva_gru_results.md` at commit `04d5008`, since overwritten by the 69.3 % run | §13 |
| DINO-WM reference | 84.0 % | `notes/results/dinowm_romer_results.md` | §11 |
| LeWM baseline of record | 87.3 % ± 7.6 (never the published 96 %) | `notes/results/inzva_pusht_results.md` | §6.1b |
| three machines agree | 87.3 / 86.7 / 87.3 % | `inzva_pusht_results.md` (RTX 3060), `truba_results.md` (V100, its first three rows), `a4000_results.md` | §6.4 |

The story, in the progress page's words: planning in bigger steps pays, most
when compute is scarce; the refinement does not. Slide 11 shows the sweep; the
three-seed numbers at 300 samples above are the earlier single point.

### Part 2: the Hi-LeWM diagnosis (`hilewm/`)

Seed 42, 50 episodes, d=50, the paper's Table 5 budget. Read
`hilewm/docs/RECONSTRUCTION.md` before quoting anything, and the slide-ready
inventory in `hilewm/docs/STATUS.md` (*Presentation material*).

| claim | number | record |
| --- | --- | --- |
| success rates, with intervals | plain CEM 36.0, Hi-LeWM-C 34.0, staged Hi-LeWM-C 46.0, oracle 70.0 | `hilewm/results/runs.csv`, `hilewm/results/summarize_eval_runs/` |
| oracle vs plain CEM | +34, p = 0.0015 | `hilewm/results/compare_eval_runs/*_oracle_vs_plain_scripted_manifest.json` |
| ...of which matched subgoal effect | +22, p = 0.035 | `*_subgoal_effect_at_paper_budget.json` |
| ...and execution mode | +12, p = 0.21 | `*_execution_mode_at_paper_budget.json` |
| oracle subgoals at low horizon 2 vs the shipped 5 | +32 for 2, p = 0.0015 | `*_lh5_vs_lh2_rerun_manifest.json` |
| Hi-LeWM-C vs plain CEM, same checkpoint and segments | exploitation x0.83 vs x9.5, first-waypoint error 22.1 vs 76.4, 10 of 10 draws, p = 0.002 | `hilewm/results/audit_dimensionality/*_draws_hilewm_c_d32_lam0.1_d50.json`, `hilewm/results/compare_draws/`; FINDINGS *Hi-LeWM-C vs plain CEM* |
| failed episodes' progress to the goal | 0.76 with expert subgoals, 0.12 with the model's | `hilewm/results/analyse_acting_npz/`; STATUS *Where we are* |
| the search exploits the model | plans scored x9.5 better than the expert's actions; macro-actions use 5-7 of 32 dimensions | `audit_dimensionality/`; FINDINGS *Synthesis so far* |
| low-level horizon 2 vs the shipped 5 | 58.0 vs 26.0 %, expert subgoals, 50-step budget | `runs.csv` rows `oracle_staged_hh2_lh2_steps50_rerun`, `oracle_staged_hh2_lh5_steps50` |
| decoded subgoals | 16-row panels, Phase A and B; slide 13 shows all 16 of the Phase B one | `hilewm/analysis/figures/*.png` |

The +34 is never shown as a subgoal effect on its own: it is +22 subgoals and
+12 execution mode (`hilewm/docs/FINDINGS.md`). Likewise, d32 exploiting more
than d8 in 10 of 10 draws is confounded (FINDINGS changelog, 2026-09-22) and
not evidence that leaving the support causes exploitation.
