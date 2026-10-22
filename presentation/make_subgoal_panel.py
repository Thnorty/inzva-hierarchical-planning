"""Build assets/sunum/subgoal-images-2rows.png, the panel on slide 15, in English.

The pptx's subgoal-gorselleri-2satir.png has Turkish labels baked in, and
nothing in the repo draws it. This copies its ten decoded frames pixel for
pixel (asserted) and redraws only the text, in the same font and colours. The
real errors (16.1/35.5 and 1.5/51.8) match rows 9 and 15 of
`hilewm/results/render_subgoals/*_draw0_hilewmc.json`; the model costs are
carried over from the original figure, which is the only record of them. Its
title said "4 rows" of a crop that shows 2, so the English title leaves that out.

From the repo root:

    hilewm/.venv/Scripts/python presentation/make_subgoal_panel.py \
        presentation/assets/sunum/subgoal-gorselleri-2satir.png \
        presentation/assets/sunum/subgoal-images-2rows.png
"""

import sys
import numpy as np
import matplotlib
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
img = Image.open(src).convert('RGB')
a = np.asarray(img).astype(int)
W, H = img.size
cols = [(33, 348), (388, 704), (743, 1062), (1099, 1418), (1457, 1772)]
rows = [(128, 444), (492, 807)]
# the green and red frames have 6px borders, 2px further out than the grey ones
rows_coloured = [(126, 446), (490, 809)]


def frame_rows(c):
    return rows_coloured if c in (2, 3) else rows


def text_colour(box, cond):
    # the darkest tenth of the text pixels, so anti-aliased edges don't wash it out
    x0, y0, x1, y1 = box
    px = a[y0:y1, x0:x1].reshape(-1, 3)
    px = px[cond(px)]
    px = px[px.sum(1).argsort()][: max(1, len(px) // 10)]
    return tuple(int(v) for v in np.median(px, 0))


grey = text_colour((90, 95, 300, 120), lambda p: p.max(1) < 200)  # "Başlangıç"
green = text_colour(
    (750, 455, 1060, 486), lambda p: (p[:, 1] - p[:, 0]) > 25
)  # expert labels
red = text_colour(
    (1105, 455, 1415, 486), lambda p: (p[:, 0] - p[:, 1]) > 40
)  # CEM labels
black = (0, 0, 0)
print('colours', grey, green, red)

canvas = Image.new('RGB', (W, H), 'white')
for c, (x0, x1) in enumerate(cols):
    for y0, y1 in frame_rows(c):
        box = (x0, y0, x1 + 1, y1 + 1)
        canvas.paste(img.crop(box), box[:2])
# keep the original's 1px outer border on the left
canvas.paste(img.crop((0, 0, 1, H)), (0, 0))

ttf = matplotlib.get_data_path() + '/fonts/ttf/DejaVuSans.ttf'


def f(size):
    return ImageFont.truetype(ttf, size)


d = ImageDraw.Draw(canvas)


def centred(cx, y_bottom, lines, font, fill, gap=4):
    hs = [d.textbbox((0, 0), t, font=font)[3] for t in lines]
    y = y_bottom - sum(hs) - gap * (len(lines) - 1)
    for t, h in zip(lines, hs):
        w = d.textlength(t, font=font)
        d.text((cx - w / 2, y), t, font=font, fill=fill)
        y += h + gap


centred(
    W / 2,
    75,
    [
        'Each row is one state · model cost: lower = the model likes it more · real error: lower = better',
        "(draw 0; rows chosen to represent CEM's median error)",
    ],
    f(22),
    black,
)
cx = [(x0 + x1) / 2 for x0, x1 in cols]
centred(cx[0], 120, ['Start'], f(20), grey)
centred(
    cx[1],
    120,
    ['Real state 25 steps later', '(through the decoder)'],
    f(20),
    grey,
)
centred(
    cx[2],
    120,
    ["Expert's plan:", 'the subgoal the model imagines'],
    f(19),
    green,
)
centred(
    cx[3], 120, ["CEM's plan:", 'the subgoal the model imagines'], f(19), red
)
centred(cx[4], 120, ['Goal'], f(20), grey)
labels = {
    (2, 0): ('2.9', '16.1'),
    (3, 0): ('1.4', '35.5'),
    (2, 1): ('3.8', '1.5'),
    (3, 1): ('52.4', '51.8'),
}
for (c, r), (cost, err) in labels.items():
    top = rows_coloured[r][1] + 5
    for i, t in enumerate([f'model cost {cost}', f'real error {err}']):
        w = d.textlength(t, font=f(17))
        d.text(
            (cx[c] - w / 2, top + i * 18),
            t,
            font=f(17),
            fill=green if c == 2 else red,
        )

# no text may overlap a frame
for c, (x0, x1) in enumerate(cols):
    for y0, y1 in frame_rows(c):
        assert (
            np.asarray(canvas)[y0 : y1 + 1, x0 : x1 + 1]
            == a[y0 : y1 + 1, x0 : x1 + 1]
        ).all()
canvas.save(out, optimize=True)
print('saved', out, canvas.size)
