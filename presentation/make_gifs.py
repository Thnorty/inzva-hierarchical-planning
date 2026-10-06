"""Turn eval episode videos into the refined deck's GIFs.

eval_wm.py saves one ``env_<i>.mp4`` per episode, each frame three panels side
by side: the agent, the expert's own run from the dataset, and the goal. This
keeps the agent panel and lays the goal over it as a faint ghost, so a viewer
sees the block being pushed into the pose it is aiming for.

The source is the Experiment A sweep's last hierarchy run (600 samples, seed
4), whose videos are in ``$STABLEWM_HOME/checkpoints/expA_hier_results/`` on the
machine that ran it. Only episodes that run scored as successes are used, and
of those, the ones where the block travels furthest.

    python presentation/make_gifs.py         --videos  $STABLEWM_HOME/checkpoints/expA_hier_results         --results $STABLEWM_HOME/checkpoints/expA_hier_results.txt
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

import re

import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent / 'assets'

AGENT = (20, 20, 236, 236)  # inner box of the left panel, in a 736x288 frame
GOAL = (496, 20, 712, 236)  # inner box of the right panel
GHOST = 0.28  # opacity of the goal laid over the agent
FPS = 15
COLOURS = 48  # Push-T is a few flat colours; a small palette keeps GIFs small


def successes(results: Path) -> list[int]:
    """Episodes the last run in an eval_wm.py results file scored as successes.

    That run is the one whose videos are on disk: each run overwrites them.
    """
    last = results.read_text(encoding='utf-8').split('==== CONFIG ====')[-1]
    flags = re.search(r"'episode_successes': array\(\[(.*?)\]\)", last, re.S)
    return [
        i
        for i, f in enumerate(re.findall(r'True|False', flags.group(1)))
        if f == 'True'
    ]


def frames(video: Path) -> list[Image.Image]:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', str(video), f'{tmp}/%03d.png'],
            check=True,
        )
        return [
            Image.open(p).convert('RGB')
            for p in sorted(Path(tmp).glob('*.png'))
        ]


def ghosted(frame: Image.Image) -> Image.Image:
    agent = np.asarray(frame.crop(AGENT), dtype=float)
    goal = np.asarray(frame.crop(GOAL), dtype=float)
    # Multiply blend at partial opacity: white stays white, the goal's block
    # shows as a faint shadow under the agent's.
    mixed = agent * (1 - GHOST + GHOST * goal / 255)
    return Image.fromarray(mixed.clip(0, 255).astype(np.uint8))


def travel(clip: list[Image.Image]) -> float:
    first = np.asarray(clip[0].convert('L'), dtype=float)
    last = np.asarray(clip[-1].convert('L'), dtype=float)
    return float(np.abs(first - last).mean())


def save_gif(clip: list[Image.Image], path: Path, hold_ms: int = 900) -> None:
    durations = [1000 // FPS] * (len(clip) - 1) + [hold_ms]
    clip = [f.quantize(COLOURS, method=Image.Quantize.MEDIANCUT) for f in clip]
    clip[0].save(
        path,
        save_all=True,
        append_images=clip[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=1,
    )
    print(f'saved {path} ({path.stat().st_size // 1024} KB)')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--videos', required=True, type=Path)
    parser.add_argument('--results', required=True, type=Path)
    args = parser.parse_args()

    clips = {
        i: [ghosted(f) for f in frames(args.videos / f'env_{i}.mp4')]
        for i in successes(args.results)
    }
    ranked = sorted(clips, key=lambda i: travel(clips[i]), reverse=True)
    print('episodes by distance travelled:', ranked[:8])
    OUT.mkdir(exist_ok=True)

    # One episode, large, for the task slide.
    hero = clips[ranked[0]]
    save_gif(
        [f.resize((432, 432), Image.LANCZOS) for f in hero],
        OUT / 'pusht-episode.gif',
    )

    # Six at once, for the opening slide.
    tile, gap, cols, rows = 216, 10, 3, 2
    picks = [clips[i] for i in ranked[: cols * rows]]
    n = min(len(c) for c in picks)
    wall = []
    for t in range(n):
        canvas = Image.new(
            'RGB',
            (cols * tile + (cols - 1) * gap, rows * tile + (rows - 1) * gap),
            (255, 255, 255),
        )
        for k, clip in enumerate(picks):
            canvas.paste(
                clip[t],
                ((k % cols) * (tile + gap), (k // cols) * (tile + gap)),
            )
        wall.append(canvas)
    save_gif(wall, OUT / 'pusht-wall.gif')


if __name__ == '__main__':
    main()
