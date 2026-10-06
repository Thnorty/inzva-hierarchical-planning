"""Experiment A: success rate against planning budget, for three planners.

The claim under test (notes/inzva-report-4.html, Experiment A) is that the
coarse-to-fine solver wins when the planning budget is small. The single point
at 300 samples (INZVA_README.md section 14) could not settle that. This sweeps
the CEM population for:

    flat     plain CEM on the fine model       inzva_gru.yaml
    coarse   plain CEM on the coarse model     inzva_gru_coarse.yaml
    hier     our coarse-to-fine solver, k = 2  inzva_gru_hier.yaml

Everything else is the locked protocol those configs already share: 50
episodes, goal 25 steps ahead, 10 environment steps of lookahead, a replan
every 10 environment steps, 30 CEM iterations. Only ``solver.num_samples``
moves, with ``solver.topk`` kept at the best 10% so the elite fraction is the
same at every budget; at 300 that is the configs' own 30, so the 300 column
re-measures the section 14 numbers. The hierarchy's fine stage keeps its
configured size at every budget, which is why the record also reports compute
as model evaluations per plan: at small budgets that stage is a large share
of the hierarchy's spend, and the comparison has to show it.

The same seed draws the same 50 episodes for every planner, so differences
are paired episode by episode and tested with an exact McNemar test.

Usage, from the repo root with STABLEWM_HOME set:

    python scripts/sweep.py run        # resumable: skips runs already recorded
    python scripts/sweep.py collect    # writes notes/results/expA_sweep_results.*
"""

import argparse
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_results import environment  # noqa: E402

PLANNERS = {
    'flat': {'config': 'inzva_gru', 'policy': 'gru_fine'},
    'coarse': {'config': 'inzva_gru_coarse', 'policy': 'gru_coarse'},
    'hier': {'config': 'inzva_gru_hier', 'policy': 'gru_fine'},
}
LABELS = {
    'flat': 'Flat CEM, fine model',
    'coarse': 'Coarse model alone',
    'hier': 'Ours, coarse then fine (k = 2)',
}
SAMPLES = (25, 50, 100, 300, 600)
SEEDS = (0, 1, 2, 3, 4)
OUT = Path('notes/results')


def topk_for(samples: int) -> int:
    """Best 10%, rounded half up, never below 2 so CEM can still fit a spread."""
    return max(2, (samples + 5) // 10)


def results_file(planner: str) -> str:
    return f'expA_{planner}_results.txt'


def results_path(planner: str) -> Path:
    home = os.environ.get('STABLEWM_HOME')
    if not home:
        raise SystemExit(
            'STABLEWM_HOME is not set; see INZVA_README.md section 3'
        )
    return Path(home) / 'checkpoints' / results_file(planner)


def parse(path: Path) -> list[dict]:
    """Every run appended to one results file, with its per-episode outcomes."""
    if not path.exists():
        return []
    runs = []
    text = path.read_text(encoding='utf-8')
    for block in text.split('==== CONFIG ====')[1:]:
        if '==== RESULTS ====' not in block:
            continue
        cfg_text, res_text = block.split('==== RESULTS ====', 1)
        cfg = yaml.safe_load(cfg_text)
        flags = re.search(
            r"'episode_successes': array\(\[(.*?)\]\)", res_text, re.DOTALL
        )
        elapsed = re.search(r'evaluation_time: ([0-9.]+)', res_text)
        outcomes = (
            [
                t == 'True'
                for t in re.findall(r'\b(True|False)\b', flags.group(1))
            ]
            if flags
            else []
        )
        runs.append(
            {
                'seed': cfg['seed'],
                'cfg': cfg,
                'outcomes': outcomes,
                'seconds': float(elapsed.group(1)) if elapsed else None,
            }
        )
    return runs


def compute_per_plan(planner: str, cfg: dict) -> int:
    """Model transition evaluations one plan costs, from the run's own config.

    Flat and coarse CEM: population x iterations x planned steps. The
    hierarchy adds, per gap, its seed evaluation, its iterations and the
    advance along the chosen actions, each k fine steps long, plus one coarse
    rollout to read off the waypoints. Image encoding is the same one call for
    every planner and is left out.
    """
    s, p = cfg['solver'], cfg['plan_config']
    if planner == 'hier':
        k = s['k']
        waypoints = p['horizon'] // k
        coarse = s['num_samples'] * s['n_steps'] * waypoints
        per_gap = k * (1 + s['fine_n_steps'] * s['fine_num_samples'] + 1)
        return coarse + waypoints + waypoints * per_gap
    return s['num_samples'] * s['n_steps'] * p['horizon']


def run(args) -> None:
    todo = []
    for planner in args.planners:
        done = {
            (r['cfg']['solver']['num_samples'], r['seed'])
            for r in parse(results_path(planner))
            if r['cfg']['solver']['topk']
            == topk_for(r['cfg']['solver']['num_samples'])
        }
        for samples in args.samples:
            for seed in args.seeds:
                if (samples, seed) not in done:
                    todo.append((planner, samples, seed))
    print(f'{len(todo)} run(s) to go', flush=True)
    for i, (planner, samples, seed) in enumerate(todo, 1):
        spec = PLANNERS[planner]
        cmd = [
            sys.executable,
            'scripts/plan/eval_wm.py',
            '--config-name',
            spec['config'],
            f'policy={spec["policy"]}',
            f'seed={seed}',
            f'solver.num_samples={samples}',
            f'solver.topk={topk_for(samples)}',
            f'output.filename={results_file(planner)}',
        ]
        start = time.time()
        print(
            f'[{i}/{len(todo)}] {planner} samples={samples} seed={seed}',
            flush=True,
        )
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode:
            print(proc.stdout[-3000:], proc.stderr[-3000:], sep='\n')
            raise SystemExit(f'run failed: {" ".join(cmd)}')
        print(f'    done in {time.time() - start:.0f} s', flush=True)


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = (
        z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    )
    return 100 * (centre - half), 100 * (centre + half)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p from the discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2**n
    return min(1.0, 2 * tail)


def collect(args) -> None:
    cells, missing = {}, []
    for planner in PLANNERS:
        by_key = {}
        for r in parse(results_path(planner)):
            n = r['cfg']['solver']['num_samples']
            if r['cfg']['solver']['topk'] != topk_for(n):
                continue  # not a sweep run
            by_key[(n, r['seed'])] = r  # a rerun replaces the earlier one
        for samples in SAMPLES:
            runs = [by_key.get((samples, s)) for s in SEEDS]
            if None in runs:
                missing.append((planner, samples))
                continue
            rates = [
                100 * sum(r['outcomes']) / len(r['outcomes']) for r in runs
            ]
            ok = sum(sum(r['outcomes']) for r in runs)
            total = sum(len(r['outcomes']) for r in runs)
            cells[(planner, samples)] = {
                'planner': planner,
                'samples': samples,
                'topk': topk_for(samples),
                'compute_per_plan': compute_per_plan(planner, runs[0]['cfg']),
                'seeds': list(SEEDS),
                'rates': rates,
                'mean': statistics.mean(rates),
                'std': statistics.stdev(rates),
                'successes': ok,
                'episodes': total,
                'wilson_95': wilson(ok, total),
                'seconds_mean': statistics.mean(r['seconds'] for r in runs),
                'outcomes': [r['outcomes'] for r in runs],
            }
    if missing:
        print('incomplete cells (not in the record):', missing)

    pairs = []
    for samples in SAMPLES:
        for a, b in (('hier', 'flat'), ('hier', 'coarse'), ('coarse', 'flat')):
            if (a, samples) not in cells or (b, samples) not in cells:
                continue
            ca, cb = cells[(a, samples)], cells[(b, samples)]
            only_a = only_b = 0
            for oa, ob in zip(ca['outcomes'], cb['outcomes']):
                if len(oa) != len(ob):
                    raise SystemExit('episode counts differ; cannot pair')
                only_a += sum(x and not y for x, y in zip(oa, ob))
                only_b += sum(y and not x for x, y in zip(oa, ob))
            pairs.append(
                {
                    'samples': samples,
                    'a': a,
                    'b': b,
                    'difference': 100
                    * (ca['successes'] - cb['successes'])
                    / ca['episodes'],
                    'only_a': only_a,
                    'only_b': only_b,
                    'mcnemar_p': mcnemar_exact(only_a, only_b),
                }
            )

    env = environment()
    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        '# Experiment A: success rate against planning budget',
        '',
        f'Generated {stamp} by `scripts/sweep.py collect`.',
        'Do not edit by hand; rerun the script instead.',
        '',
        'Source: `$STABLEWM_HOME/checkpoints/expA_{flat,coarse,hier}_results.txt`',
        '',
        '## Environment',
        '',
        '| | |',
        '|---|---|',
        f'| commit (at collection) | `{env.get("commit")}` |',
        f'| torch | `{env.get("torch")}` |',
        f'| cuda | `{env.get("cuda")}` |',
        f'| gpu | `{env.get("gpu")}` |',
        '',
        f'Seeds {", ".join(map(str, SEEDS))}, 50 episodes each, so {50 * len(SEEDS)} '
        'episodes per cell. CEM: 30 iterations, top 10% kept. Compute is model '
        'transition evaluations per plan.',
        '',
        '## Success rate',
        '',
        '| Planner | Samples | Compute / plan | Seeds | Mean | Std | Pooled | 95% interval | Seconds / run |',
        '|---|---|---|---|---|---|---|---|---|',
    ]
    for planner in PLANNERS:
        for samples in SAMPLES:
            c = cells.get((planner, samples))
            if not c:
                continue
            lo, hi = c['wilson_95']
            lines.append(
                f'| {LABELS[planner]} | {samples} | {c["compute_per_plan"]:,} '
                f'| {", ".join(f"{r:.0f}" for r in c["rates"])} '
                f'| {c["mean"]:.1f}% | {c["std"]:.1f} '
                f'| {c["successes"]}/{c["episodes"]} | {lo:.1f} to {hi:.1f} '
                f'| {c["seconds_mean"]:.0f} |'
            )
    lines += [
        '',
        '## Paired differences',
        '',
        'Same seed, same episodes. Only-A and only-B are the episodes one planner '
        'solved and the other did not.',
        '',
        '| Samples | A | B | A - B, points | Only A | Only B | McNemar p |',
        '|---|---|---|---|---|---|---|',
    ]
    for p in pairs:
        lines.append(
            f'| {p["samples"]} | {p["a"]} | {p["b"]} | {p["difference"]:+.1f} '
            f'| {p["only_a"]} | {p["only_b"]} | {p["mcnemar_p"]:.3g} |'
        )
    lines += [
        '',
        '## Commands',
        '',
        '```bash',
        'python scripts/sweep.py run',
        'python scripts/sweep.py collect',
        '```',
        '',
    ]
    (OUT / 'expA_sweep_results.md').write_text(
        '\n'.join(lines), encoding='utf-8', newline='\n'
    )
    record = {
        'generated': datetime.now(timezone.utc).isoformat(),
        'environment': env,
        'cells': [
            {k: v for k, v in c.items() if k != 'outcomes'}
            for c in cells.values()
        ],
        'pairs': pairs,
    }
    (OUT / 'expA_sweep_results.json').write_text(
        json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n'
    )
    print(f'wrote {OUT / "expA_sweep_results.md"} ({len(cells)} cells)')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser(
        'run', help='run every missing (planner, samples, seed)'
    )
    r.add_argument(
        '--planners', nargs='+', default=list(PLANNERS), choices=list(PLANNERS)
    )
    r.add_argument('--samples', nargs='+', type=int, default=list(SAMPLES))
    r.add_argument('--seeds', nargs='+', type=int, default=list(SEEDS))
    sub.add_parser('collect', help='write the tracked record')
    args = parser.parse_args()
    {'run': run, 'collect': collect}[args.cmd](args)


if __name__ == '__main__':
    main()
