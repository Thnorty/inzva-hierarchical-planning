# presentation/

The final showcase deck, as a self-contained HTML page, with the record behind
every number on it.

| path | what it is |
| --- | --- |
| `final_sunumu.html` | **the deck**: 19 slides, 12:45. The final presentation, rebuilt from `Hi-LeWM Final Sunumu.pptx` in this folder's design system. In English since 2026-10-22; it was Turkish before (see *Language*). The speech script (`Hi-LeWM Final Sunumu Konuşma Metni.txt`, kept outside this repo) is numbered to match it slide for slide |
| `assets/sunum/` | what the deck needs: the PushT gif, the two data figures in English (`failure-map.png`, `subgoal-images-2rows.png`), and the three hierarchy-chain frames cropped out of the pptx's example figure. The pptx's Turkish figures stay here as the panel's source and as a record; the deck no longer shows them |
| `make_failure_map.py`, `make_subgoal_panel.py` | draw the two English figures; see *The two data figures* |
| `assets/inzva.webp` | the inzva wordmark, in the top-right corner of every slide. White artwork on transparency, inverted in CSS on the light slides — see below |
| `assets/qr/` | the QR codes, named for where they lead: `slides.svg` (this deck's web address; left of the wordmark on slides 1–18, and on the closing slide), `repo.svg` (the GitHub repo), and `linkedin-defne.png`, `linkedin-oguz.png`, `linkedin-arda.png` (our LinkedIn profiles). All five are on the closing slide — see *The QR codes* |
| `assets/favicon.png` | the browser-tab icon: `assets/inzva-logo.webp`, the inzva ring, white on the dark slides' colour so it shows on light and dark tabs alike |
| `assets/inzva-logo.webp` | the inzva ring on its own, white on transparency; the source of the favicon |
| `assets/team/` | **put `defne.jpg`, `oguz.jpg` and `arda.jpg` here**, square crops work best. Until then the deck shows initials |
| `previous/presentation-3.pptx` | presentation 3, as given ("Proj Presentation #3"): Push-T, VLA vs world models, the GRU predictor, CEM, MPC, temporal hierarchy |
| `../notes/inzva-report-4.html` | the spec sent before presentation 4. Frozen, never edited; its 40-step horizon and stride 8 are out of date (`INZVA_README.md` §13) |

### What used to be here

`index.html` was the English deck: 17 slides and 11:25, the project for a
general audience in the inzva house structure. It is gone, because the final
presentation is given from `final_sunumu.html` and one deck is easier to keep
true than two. The three figures only it used went with it
(`pusht-wall.gif`, `pusht-episode.gif`, `subgoal-strip.png`), and so did
`make_gifs.py` and `make_subgoal_strip.py`, which existed only to generate
them. Before that there was a shorter deck, one with the statistics printed on
the slides, and an `index-light.html` with a `make_light.py` to write it.

None of the numbers are lost. The intervals, p-values and per-seed counts live
in `notes/results/` and `hilewm/results/`, and the tables at the bottom of this
file say which record holds which. Recover any deleted file from git history if
a question ever needs it.

## Presenting

Open `final_sunumu.html` in a browser, from this folder so it finds `assets/`.
The gif plays and loops on its own. It needs the internet only for its two
fonts, and falls back to Georgia and Consolas without them.

| key | does |
| --- | --- |
| → , space, Page Down, ↓ | next slide (a presenter clicker sends these) |
| ← , Page Up, ↑ | previous slide |
| Home / End | first / last slide |
| F | full screen |

**There is no speaker-notes panel and no rehearsal clock.** The script is the
notes, read from its own file, so there is no `N` key; the deck that had one is
the deleted `index.html`. The controls are a bare `←  n / 19  →` in the
bottom-left corner that fades out after a few seconds of no mouse movement; its
4px inset is as large as it goes before the arrow overlaps the footer's source
line. Across the top is one progress segment per slide, filling as you advance.

`final_sunumu.html#5` opens on slide 5.

### Online

The deck is also served at **https://thnorty.github.io/inzva-hierarchical-planning/**,
the address the QR code on the slides points at. `.github/workflows/pages.yaml`
publishes `final_sunumu.html` there as `index.html`, with `assets/`, on every
push to `main` that touches either. Nothing else in the repo is published. The
web copy is only as current as `main`, so push before handing out the link.
`…/inzva-hierarchical-planning/#5` opens on slide 5 there too.

## The deck

Rebuilt from `Hi-LeWM Final Sunumu.pptx` so that the deck and the speech script
agree. It follows the pptx's own order, and is not a translation of
the old English deck, which was cut for a different audience. It had 20
slides until 2026-10-23, when the method slide (*How we examined Hi-LeWM*,
pptx 11) was cut: its two questions moved onto the stage-2 question slide
(12), and the check that we reproduced two of the paper's numbers (36.0% vs
38.7%, 70.0% vs 73.3%) left the slides and lives on only as a prepared
answer in the script.

### Light and dark

The deck is **always light**, whatever the machine is set to: there is no
`prefers-color-scheme` rule in it, so it needs no `data-theme` pin either. On a
projector or printed to PDF that is what you want. Two slides are deliberately
dark, the stage-2 question (12) and the closing *Questions?* (19); they carry
`class="slide dark"`, which redefines the palette variables on the section
itself. Add or remove that class to change which slides invert — nothing else
needs touching.

A caveat worth knowing before judging the result: a browser dark-mode extension
will re-darken a light page, and it does so unevenly — inline SVG fills survive
while the page background does not. If the deck looks half dark, check the
extension before changing the CSS.

### The wordmark

The inzva wordmark sits in the top-right corner of all 19 slides, on the
eyebrow line. It is a single `<img class="brand">` at the end of `.stage`, not
a copy per slide: only one slide is visible at a time, so one element is enough
and slides stay free of boilerplate. `assets/inzva.webp` is white artwork on a
transparent background, so it would vanish on the seventeen light slides as it
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

### The QR codes

`assets/qr/slides.svg` encodes https://thnorty.github.io/inzva-hierarchical-planning/
(see *Online*). Like the wordmark it is one `<img class="qr">` at the end of
`.stage`, 18px left of the mark, on every slide but the closing one. The
closing slide shows all five codes in one row at 200px (about 35 cm on a 3 m
screen): *Slides* and *Repo* (`qr/repo.svg`,
https://github.com/Thnorty/inzva-hierarchical-planning), a thin divider, then
the three LinkedIn codes, each with that person's photo in the middle and
their name underneath.
Both addresses are also written out under *Questions?*. Only the deck's code
is in the corner, because two small codes side by side leave people guessing
which to scan. The repo code was made with `segno` to match the deck's:
version 4, error correction M, a 3-module margin, so the two look alike side
by side. The LinkedIn codes are LinkedIn's own, error-correction level H, with that
person's photo (`team/*.jpg`, as a squircle) in place of the LinkedIn logo, inside
the logo's own box, so no more of the code is covered than before. They decode
with zxing and WeChat's reader at full size, at 100px and blurred with noise,
and OpenCV's basic reader fails on exactly the cases where it also failed on
the logo originals (in git history at `91c4cc3`). The
corner code is not dimmed like the mark,
since it has to scan: on light slides `mix-blend-mode:multiply` melts its white
background into the paper colour, and on the two dark slides it stays a white
square, which is also the light margin a camera needs.

**Don't shrink it below 80px.** Of 52, 64, 72 and 80px, only 80px decoded
with OpenCV's basic QR detector on a 1920×1080 render. At 80px the WeChat
detector (`opencv-contrib`), which reads more like a phone camera, decodes it
on all 20 slides the deck then had, at both 1600×900 and 1920×1080. `top:40px` keeps its bottom edge (120px) above
where the titles start (~121px). If the address ever changes, regenerate the
SVG. Keep QR codes out of `.jpg`: `.gitignore` ignores `*.jpg`, so a JPEG code
never reaches the web copy.

### Conventions

Three worth knowing before editing it:

- **Language.** English, written as English rather than translated
  sentence by sentence; the Turkish deck is in git history before
  2026-10-22. The technical terms are the ones the Turkish deck already used
  (`subgoal`, `episode`, `action`, `reward`, `expert`, `score`, `draw`,
  `threshold`, `planner`), so the script's terms still match. The talk is
  given in Turkish, so the speech script stays fully Turkish even where it
  reads out a slide's sentence. Percentages are written English-style,
  `82%`, including in the chart on slide 15.
- **Corner numbers.** Every slide is numbered, 1 to 19, matching the deck
  position — the cover is 1 and the team slide 2, where the pptx left both
  blank and numbered the rest 1 to 18. So a slide's corner number is its
  pptx number plus two up to slide 12, and plus one after it, since pptx 11
  was cut; the `<!-- n -->` comments in the HTML keep the pptx numbers. And `final_sunumu.html#5` is the slide that says 5. The
  number comes from `data-no` on each `<section>`, kept explicit so the pptx's
  numbering can be restored in one place if it is ever wanted.
- **Figures.** The schematics are inline SVG, drawn in the deck's palette, so
  they follow light and dark like everything else. Only the three real-data
  figures are images. The pptx had the two-time-scales figure as a screenshot
  of the old English deck's; this one redraws it in the deck's palette.

### Timing

The budgets are the script's and add up to **12:45**. It was 14:20 after the
two slides cut from the pptx (*İki örnek: Episode 9* and the unnumbered
*Episode 27*) and the 15 seconds slide 4 gained for Ha & Schmidhuber's 2018
*World Models*; then Oğuz's slides 8–12 were tightened to 13:05 in the script
alone, and on 2026-10-23 slide 13 was cut and 11 shortened, which gave 12:40, and slide 10 gained 5 seconds explaining that the fine model fills the gaps.
Since then `data-time` matches the script slide for slide. The script is
numbered 1 to 19 to match the corners, with its section table, time total and
cross-references updated with it. Keep the two in step: a
slide added or moved here needs the same change there.

Each `<section>` still carries its budget as `data-time` in seconds, but with
the clock gone nothing reads it any more. It is kept as a record of the plan,
and as what a timer would read from if one is ever wanted back.

The two findings are labelled: slide 13 is *Finding 1* (the planner fools the
model) and slide 16 is *Finding 2* (failures come from two levels). They are the
same two conclusions the *Conclusions* slide numbers 1 and 2. The pptx had only a
*Bulgu 1*, with nothing answering it.

### The two data figures

The pptx's two real-data figures had Turkish labels baked into the image, so
the English deck uses rebuilt versions:

- **`failure-map.png`** (slide 16) is redrawn from the data by
  `make_failure_map.py`: the staged Hi-LeWM run at d = 50 with a 100-step
  budget, `hilewm/results/colab/acting/generated_subgoal_acting_d50_hh2_lh2_budget100_seed42.npz`.
  Both axes are fractions of the start-to-goal distance, as in
  `hilewm/analysis/analyse_acting_npz.py`. It reproduces the Turkish
  `basarisizlik-haritasi.png` point for point, and the script asserts the
  12/9, 7/7 and 31/10 the slide quotes.
- **`subgoal-images-2rows.png`** (slide 14) is rebuilt by
  `make_subgoal_panel.py` from `subgoal-gorselleri-2satir.png`: the ten
  decoded frames are copied pixel for pixel and only the text is redrawn.
  Re-decoding the frames would need the decoder probe and could drift from
  what was shown. The real errors match `hilewm/results/render_subgoals/`
  (draw 0, rows 9 and 15); the four model costs exist only in the original
  figure. That figure's title said four rows of a crop that holds two
  (`subgoal-gorselleri.png` was exported cropped); the English title no longer
  says how many.

## The rule for slides

Every number on a slide comes from a record, never from memory or a terminal
snippet. The project's two parts keep their records in different places and
use different goal offsets (d=25 for our planner, d=50 for Hi-LeWM), so **their
success rates never share an axis**. The 16-row panels are no longer shown on
any slide: the deck uses the pptx's own two-row figure instead, and the English
deck that carried `subgoal-strip.png` is gone.

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
| our GRU's size, slide 11 | 7M: 7,125,200, the fine and coarse models with their shared encoder and projector counted once (each alone is 6,709,662; both in full 13,419,344). Replaces an 11M that nothing in the code supported | counted by building both from `scripts/train/config/gru.yaml` and `gru_coarse.yaml`, unchanged since `0a88e1a`; `scripts/train_gru.py` copies and freezes the encoder and projector for the coarse model | §6.5 |
| LeWM baseline of record | 87.3 % ± 7.6 (never the published 96 %) | `notes/results/inzva_pusht_results.md` | §6.1b |
| three machines agree | 87.3 / 86.7 / 87.3 % | `inzva_pusht_results.md` (RTX 3060), `truba_results.md` (V100, its first three rows), `a4000_results.md` | §6.4 |

The story, in the progress page's words: planning in bigger steps pays, most
when compute is scarce; the refinement does not. The sweep itself was on slide
11 of the deleted English deck and is not in `final_sunumu.html`, which carries
part 1 only as the GRU-against-DINO-WM comparison on its slide 11. The
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
| decoded subgoals | 16-row panels, Phase A and B | `hilewm/analysis/figures/*.png` |

The +34 is never shown as a subgoal effect on its own: it is +22 subgoals and
+12 execution mode (`hilewm/docs/FINDINGS.md`). Likewise, d32 exploiting more
than d8 in 10 of 10 draws is confounded (FINDINGS changelog, 2026-09-22) and
not evidence that leaving the support causes exploitation.
