"""Draw assets/sunum/failure-map.png, the scatter plot on slide 17, in English.

It replaces the pptx's Turkish basarisizlik-haritasi.png and is drawn from the
same run: the staged Hi-LeWM run at d = 50 with a 100-step budget (48 % on
slide 16), stage 1, first 25 steps. The counts it prints are asserted against
the slide's 12/9, 7/7 and 31/10, so a different input fails loudly.

From the repo root, with the Hi-LeWM environment (it has matplotlib):

    hilewm/.venv/Scripts/python presentation/make_failure_map.py \
        hilewm/results/colab/acting/generated_subgoal_acting_d50_hh2_lh2_budget100_seed42.npz \
        presentation/assets/sunum/failure-map.png
"""

import sys
import numpy as np
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt


def mse(a, b):
    return ((a - b) ** 2).mean(-1)


npz, out = sys.argv[1], sys.argv[2]
d = np.load(npz)
sg = d['generated_stage_targets'][:, 0]
ok = d['episode_successes'].astype(bool)
unit = mse(d['start_latent'], d['goal_latent'])  # start-to-goal distance
x = ((sg[:, None] - d['future_latents']) ** 2).mean(-1).min(
    1
) / unit  # subgoal vs expert path
y = (
    mse(d['stage_end_actual_latents'][0], sg) / unit
)  # where the agent got vs subgoal
T = 0.25
R, TL = x > T, (x <= T) & (y > T)
BL = ~R & ~TL
counts = {
    k: (int(m.sum()), int((m & ~ok).sum()))
    for k, m in (('R', R), ('TL', TL), ('BL', BL))
}
assert counts == {'R': (12, 9), 'TL': (7, 7), 'BL': (31, 10)}, counts

fig, ax = plt.subplots(figsize=(6.2, 5.0), dpi=150)
ax.set_xscale('log')
ax.set_yscale('log')
ax.scatter(
    x[ok], y[ok], s=22, c='#2e9b55', marker='o', label='succeeded', zorder=3
)
ax.scatter(
    x[~ok], y[~ok], s=22, c='#d64550', marker='x', label='failed', zorder=3
)
ax.axvline(T, ls='--', c='0.55', lw=1)
ax.axhline(T, ls='--', c='0.55', lw=1)
ax.set_xlim(0.0085, 0.47)
ax.set_ylim(0.008, 12)
ax.set_title(
    'Each point is one episode (stage 1, first 25 steps; threshold 0.25)',
    fontsize=10.5,
)
ax.set_xlabel(
    "How far the model's subgoal is from the expert's path →\n(larger = meaningless subgoal)",
    fontsize=9.5,
)
ax.set_ylabel(
    'How far the agent stayed from its subgoal →\n(larger = not reached)',
    fontsize=9.5,
)
kw = dict(transform=ax.transAxes, fontsize=8.6, va='top')
ax.text(
    0.02,
    0.975,
    f'MEANINGFUL SUBGOAL, NOT REACHED\n(low level to blame)\n{counts["TL"][0]} episodes, {counts["TL"][1]} failed',
    color='#2a86a8',
    **kw,
)
ax.text(
    0.98,
    0.975,
    f'MEANINGLESS SUBGOAL\n(high level to blame)\n{counts["R"][0]} episodes, {counts["R"][1]} failed',
    color='#d64550',
    ha='right',
    **kw,
)
ax.text(
    0.02,
    0.025,
    f'On track after stage 1\n{counts["BL"][0]} episodes, {counts["BL"][1]} failed',
    color='0.35',
    transform=ax.transAxes,
    fontsize=8.6,
    va='bottom',
)
ax.legend(loc='lower right', fontsize=8.6)
fig.tight_layout()
fig.savefig(out, dpi=150)
print('saved', out, counts)
