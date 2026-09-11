"""Verify the PushT expert dataset through the repo's own dataset API.

Confirms the facts recorded in INZVA_README.md section 5.1, so that a
re-download differing from ours is caught immediately rather than after three
weeks of training on it.

Checks:

1. ``load_dataset`` opens the HDF5 and reports episode/step counts.
2. Column names, shapes and dtypes.
3. ``proprio`` really is ``[state[:2], state[-2:]]``.
4. Actions drive the state (correlation with agent displacement), and how far
   outside the declared ``Box(-1, 1)`` action space the expert data goes. The
   action check scans every step, so its numbers are exact, not sampled.
5. ``state`` and ``pixels`` are aligned, by projecting the agent position into
   render coordinates and comparing against the rendered agent blob.

Also writes an annotated frame strip and an episode video next to the report,
so the alignment can be eyeballed rather than taken on faith.

Usage:
    python scripts/verify_dataset.py [--out DIR] [--episode N]
"""

import argparse
import json
import os

import numpy as np

import stable_worldmodel as swm

# PushT renders a 512-unit window; state positions are in those units.
WINDOW_SIZE = 512
# step() sets target = agent_pos + action * ACTION_SCALE, then PD-controls to it.
ACTION_SCALE = 100
# The env declares Box(-1, 1); the expert data does not fully respect it.
ACTION_BOX = 1.0


def agent_centroid(frame):
    """Centroid of the RoyalBlue agent disc in an HWC uint8 frame.

    Args:
        frame: One rendered frame, ``(H, W, 3)`` uint8.

    Returns:
        ``(x, y)`` in pixel coordinates, or ``None`` if the agent is not
        visible (fewer than five matching pixels).
    """
    f = frame.astype(np.int32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    mask = (b > 120) & (b - r > 60) & (b - g > 40)
    if mask.sum() < 5:
        return None
    ys, xs = np.nonzero(mask)
    return xs.mean(), ys.mean()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default='.', help='where to write outputs')
    parser.add_argument(
        '--episode', type=int, default=0, help='episode to inspect and render'
    )
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    home = os.environ.get('STABLEWM_HOME')
    if not home:
        raise SystemExit(
            'STABLEWM_HOME is not set; see INZVA_README.md section 3'
        )
    path = os.path.join(home, 'datasets', 'pusht_expert_train.h5')

    print(f'opening {path}', flush=True)
    ds = swm.data.load_dataset(path)

    report = {
        'path': path,
        'size_bytes': os.path.getsize(path),
        'reader': type(ds).__name__,
        'num_episodes': len(ds.lengths),
        'num_steps': int(ds.lengths.sum()),
        'ep_len_min': int(ds.lengths.min()),
        'ep_len_max': int(ds.lengths.max()),
        'ep_len_mean': float(ds.lengths.mean()),
        'columns': list(ds.column_names),
    }
    print('reader        : {reader}'.format(**report))
    print('episodes      : {num_episodes}'.format(**report))
    print('steps         : {num_steps}'.format(**report))
    print(
        'episode length: {ep_len_min} to {ep_len_max}, '
        'mean {ep_len_mean:.1f}'.format(**report)
    )
    print('columns       : {columns}'.format(**report))

    # -- one full episode
    ep = ds.load_episode(args.episode)
    print(f'\n--- episode {args.episode} ---')
    report['shapes'] = {}
    for name, value in ep.items():
        arr = np.asarray(value)
        print(f'  {name:<12} {tuple(arr.shape)!s:<20} {arr.dtype}')
        report['shapes'][name] = [list(arr.shape), str(arr.dtype)]

    action = np.asarray(ep['action'], dtype=np.float64)
    state = np.asarray(ep['state'], dtype=np.float64)
    proprio = np.asarray(ep['proprio'], dtype=np.float64)
    # On disk pixels are HWC, but HDF5Dataset permutes them to CHW on read
    # (data/formats/hdf5.py:130). Everything below wants HWC again.
    pixels = np.transpose(np.asarray(ep['pixels']), (0, 2, 3, 1))
    report['pixels_layout'] = (
        'HWC on disk; the reader returns CHW (T, 3, 224, 224)'
    )

    # -- proprio is a view of state, carrying no extra information
    stacked = np.concatenate([state[:, :2], state[:, -2:]], axis=1)
    diff = float(np.abs(proprio - stacked).max())
    print(f'\nmax |proprio - [state[:2], state[-2:]]| = {diff}')
    report['proprio_state_max_abs_diff'] = diff

    # -- actions drive the state
    disp = state[1:, :2] - state[:-1, :2]
    n = min(len(disp), len(action) - 1)
    disp, act = disp[:n], action[:n]
    for i, axis in enumerate('xy'):
        c = float(np.corrcoef(act[:, i], disp[:, i])[0, 1])
        print(f'corr(action_{axis}, delta_agent_{axis}) = {c:.4f}')
        report[f'corr_action_disp_{axis}'] = c
    big = np.abs(act) > 0.2
    ratio = float(np.median(np.abs(disp[big]) / np.abs(act[big])))
    print(
        f'median |displacement| / |action| = {ratio:.1f} '
        f'(commanded scale is {ACTION_SCALE}; PD control undershoots)'
    )
    report['median_disp_over_action'] = ratio

    # -- action range over every step, not a sample
    # The action column is 2 float32 per step, so the whole thing is under
    # 20 MB. Sampling episodes here would only make the numbers irreproducible.
    all_actions = ds.get_col_data('action').astype(np.float64)
    lo, hi = all_actions.min(0), all_actions.max(0)
    out_of_box = int((np.abs(all_actions) > ACTION_BOX).any(axis=1).sum())
    total = len(all_actions)
    print(f'\n--- actions over all {total} steps ---')
    print(f'min {lo}  max {hi}')
    print(f'std {all_actions.std(0)}')
    print(
        f'steps outside Box(-1, 1): {out_of_box} / {total} '
        f'({100 * out_of_box / total:.4f}%)'
    )

    # How far outside the box does the solver's own sampling reach? CEM draws
    # N(0, var_scale) in units normalised by this std, so the box edge sitting
    # many sigma away is why nothing needs clipping. See README section 5.3.
    edge_sigma = (ACTION_BOX - all_actions.mean(0)) / all_actions.std(0)
    print(f'box edge in normalised units: {edge_sigma} sigma')
    report.update(
        action_min=lo.tolist(),
        action_max=hi.tolist(),
        action_std=all_actions.std(0).tolist(),
        action_out_of_box=out_of_box,
        action_out_of_box_frac=out_of_box / total,
        action_box_edge_sigma=edge_sigma.tolist(),
    )

    # -- state / pixels alignment
    height, width = pixels.shape[1], pixels.shape[2]
    scale = width / WINDOW_SIZE
    print(f'\npixels {height}x{width}, window {WINDOW_SIZE}, scale {scale}')
    errors = []
    print('  t   state->px(x,y)      blob(x,y)        err_px')
    for t in range(0, len(pixels), max(1, len(pixels) // 12)):
        found = agent_centroid(pixels[t])
        if found is None:
            continue
        ex, ey = state[t, 0] * scale, state[t, 1] * scale
        err = float(np.hypot(found[0] - ex, found[1] - ey))
        errors.append(err)
        print(
            f'{t:3d}  ({ex:6.1f},{ey:6.1f})  '
            f'({found[0]:6.1f},{found[1]:6.1f})  {err:6.2f}'
        )
    if errors:
        print(
            f'mean/max alignment error: {np.mean(errors):.2f} / '
            f'{np.max(errors):.2f} px over {len(errors)} frames'
        )
        report['align_mean_px_err'] = float(np.mean(errors))
        report['align_max_px_err'] = float(np.max(errors))

    # -- eyeballable outputs
    try:
        import imageio.v2 as imageio

        video = os.path.join(args.out, f'pusht_ep{args.episode}.mp4')
        imageio.mimsave(
            video, [np.ascontiguousarray(f) for f in pixels], fps=10
        )
        print(f'\nwrote {video}')
        report['video'] = video
    except Exception as exc:  # noqa: BLE001 - optional output only
        print(f'video write skipped: {type(exc).__name__}: {exc}')

    try:
        from PIL import Image, ImageDraw

        tiles = []
        marks = [0, len(pixels) // 3, 2 * len(pixels) // 3, len(pixels) - 1]
        for i in marks:
            im = Image.fromarray(np.ascontiguousarray(pixels[i])).convert(
                'RGB'
            )
            draw = ImageDraw.Draw(im)
            ax, ay = state[i, 0] * scale, state[i, 1] * scale
            bx, by = state[i, 2] * scale, state[i, 3] * scale
            draw.ellipse(
                [ax - 6, ay - 6, ax + 6, ay + 6], outline=(255, 0, 0), width=2
            )
            draw.ellipse(
                [bx - 6, by - 6, bx + 6, by + 6], outline=(0, 255, 0), width=2
            )
            draw.text((3, 3), f't={i}', fill=(255, 200, 0))
            tiles.append(np.asarray(im))
        strip = os.path.join(args.out, f'pusht_ep{args.episode}_strip.png')
        Image.fromarray(np.concatenate(tiles, axis=1)).save(strip)
        print(
            f'wrote {strip} (red = state agent pos, green = state block pos)'
        )
        report['strip'] = strip
    except Exception as exc:  # noqa: BLE001 - optional output only
        print(f'strip write skipped: {type(exc).__name__}: {exc}')

    out = os.path.join(args.out, 'dataset_report.json')
    with open(out, 'w') as fh:
        json.dump(report, fh, indent=2)
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
