"""Check that the current PushT env is the env that generated the dataset.

Several commits between the one that published the 96% Push-T baseline
(`44c45bd`) and our pin (`6f1e499`) touched the PushT block geometry and the
success criterion. If any of them changed the task, our numbers are not
comparable to the published one and no amount of solver tuning would explain
the difference.

The test is direct: set the environment to a state recorded in the dataset,
render it, and compare against the frame the dataset recorded for that same
step. A geometry change shows up immediately as a shape that does not overlap.

A small residual is expected and fine. Rendering is antialiased, so edges
differ by a few intensity levels even when the geometry is identical. What
matters is the fraction of pixels that differ substantially, which should be
well under one percent and confined to outlines.

Usage:
    python scripts/check_env_matches_dataset.py [--out DIR] [--episode N]
"""

import argparse
import os

import gymnasium as gym
import numpy as np

import stable_worldmodel as swm

# A pixel differing by more than this is a real disagreement rather than
# antialiasing on a shape outline.
INTENSITY_TOLERANCE = 24
# Above this fraction of substantially-differing pixels, the environments are
# not the same. Measured agreement at 6f1e499 is 0.30% to 0.39% depending on the
# frame, and the exact figure shifts by a few hundredths of a percent between
# checkouts even with identical sources and identical packages: SDL picks
# rendering code paths at runtime, so edge antialiasing is not bit-stable. Read
# the pass/fail, not the percentage. The threshold sits about 5x above what a
# matching env produces, and a real geometry change misses by far more.
FRACTION_THRESHOLD = 0.02


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='.', help='where to write the figure')
    parser.add_argument('--episode', type=int, default=0)
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    home = os.environ.get('STABLEWM_HOME')
    if not home:
        raise SystemExit(
            'STABLEWM_HOME is not set; see INZVA_README.md section 3'
        )

    ds = swm.data.load_dataset(
        os.path.join(home, 'datasets', 'pusht_expert_train.h5')
    )
    ep = ds.load_episode(args.episode)
    states = np.asarray(ep['state'], dtype=np.float64)
    # The reader hands back CHW; rendering and comparison want HWC.
    pixels = np.transpose(np.asarray(ep['pixels']), (0, 2, 3, 1))

    env = gym.make('swm/PushT-v1', render_mode='rgb_array').unwrapped
    env.reset(seed=0)
    shape = env.shapes[int(env.variation_space['block']['shape'].value)]
    print(f'block shape : {shape}')
    print(f'block scale : {env.variation_space["block"]["scale"].value}')

    height, width = pixels.shape[1], pixels.shape[2]
    steps = [0, len(pixels) // 3, 2 * len(pixels) // 3, len(pixels) - 1]

    worst = 0.0
    print('\n  t   mean|diff|   pixels differing')
    for t in steps:
        env._set_state(states[t])
        frame = render_at(env, height, width)
        diff = np.abs(frame.astype(np.int16) - pixels[t].astype(np.int16))
        fraction = float((diff.max(axis=2) > INTENSITY_TOLERANCE).mean())
        worst = max(worst, fraction)
        print(f'{t:3d}   {diff.mean():9.2f}   {100 * fraction:8.2f}%')

    print(f'\nworst differing-pixel fraction: {100 * worst:.2f}%')
    if worst < FRACTION_THRESHOLD:
        print('PASS: the env matches the one that generated the dataset')
    else:
        print('FAIL: the env differs from the one that generated the dataset')

    write_figure(env, states, pixels, steps[len(steps) // 2], args.out)

    raise SystemExit(0 if worst < FRACTION_THRESHOLD else 1)


def render_at(env, height, width):
    """Render the env and match the dataset's frame size."""
    frame = env.render()
    if frame.shape[:2] != (height, width):
        from PIL import Image

        frame = np.asarray(
            Image.fromarray(frame).resize((width, height), Image.BILINEAR)
        )
    return frame


def write_figure(env, states, pixels, t, out_dir):
    """Save a dataset / env / difference strip for eyeballing."""
    try:
        from PIL import Image

        env._set_state(states[t])
        frame = render_at(env, pixels.shape[1], pixels.shape[2])
        delta = np.abs(
            frame.astype(np.int16) - pixels[t].astype(np.int16)
        ).astype(np.uint8)
        strip = np.concatenate([pixels[t], frame, delta], axis=1)
        path = os.path.join(out_dir, 'env_vs_dataset.png')
        Image.fromarray(strip).save(path)
        print(f'wrote {path} (dataset | current env | absolute difference)')
    except Exception as exc:  # noqa: BLE001 - figure is optional
        print(f'figure skipped: {type(exc).__name__}: {exc}')


if __name__ == '__main__':
    main()
