"""Re-lay the 16-row decoded-subgoal panel as one wide strip for a slide.

The source is hilewm's own figure (render_subgoals.py, main checkpoint, d=50,
draw 0, Phase B probe, with Hi-LeWM-C). Its columns are frame t, probe(z_t),
probe(z_true), probe(expert), probe(CEM), probe(Hi-LeWM-C), probe(z_goal). This
keeps four of them and transposes, so every one of the 16 segments is shown:
nothing is selected.

    hilewm/.venv/Scripts/python presentation/make_subgoal_strip.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / 'hilewm/analysis/figures'
    / 'subgoals_pusht_hi_lewm_epoch15_weights_phase_b_d50_draw0_16rows_hilewmc.png'
)
OUT = Path(__file__).resolve().parent / 'assets' / 'subgoal-strip.png'

N_COLS, N_ROWS = 7, 16
# probe(z_true), probe(expert), probe(CEM), probe(Hi-LeWM-C)
KEEP = [2, 3, 4, 5]
CELL, INSET, GAP = 120, 4, 6


def main() -> None:
    panel = Image.open(SOURCE).convert('RGB')
    w, h = panel.size[0] / N_COLS, panel.size[1] / N_ROWS
    strip = Image.new(
        'RGB',
        (
            N_ROWS * CELL + (N_ROWS - 1) * GAP,
            len(KEEP) * CELL + (len(KEEP) - 1) * GAP,
        ),
        (255, 255, 255),
    )
    for seg in range(N_ROWS):
        for out_row, col in enumerate(KEEP):
            box = (
                round(col * w) + INSET,
                round(seg * h) + INSET,
                round((col + 1) * w) - INSET,
                round((seg + 1) * h) - INSET,
            )
            cell = panel.crop(box).resize((CELL, CELL), Image.LANCZOS)
            strip.paste(cell, (seg * (CELL + GAP), out_row * (CELL + GAP)))
    OUT.parent.mkdir(exist_ok=True)
    strip.save(OUT, optimize=True)
    print(f'saved {OUT} {strip.size}')


if __name__ == '__main__':
    main()
