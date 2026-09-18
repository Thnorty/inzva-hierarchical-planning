"""Collect eval runs into a tracked, durable results record.

``eval_wm.py`` appends a config dump and a metrics block to
``$STABLEWM_HOME/checkpoints/<policy-owner>/<output.filename>`` after every
run. That file has everything worth keeping, but it lives under
``$STABLEWM_HOME``, which is gitignored, so it is one ``git clean -xdf`` or one
fresh clone away from gone, and nobody else on the team can see it.

This reads those files and writes a summary into the repo, where it is tracked:
a Markdown table for people and a JSON blob for scripts. It records the commit
SHA and the library versions alongside the numbers, because "same commit" did
not turn out to mean "same install" (see INZVA_README.md section 7).

Usage:
    python scripts/collect_results.py
    python scripts/collect_results.py --results-file pusht_results.txt
    python scripts/collect_results.py --out notes/results
"""

import argparse
import json
import os
import posixpath
import re
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

DEFAULT_OUT = Path('notes/results')


def git_sha() -> str:
    """Short SHA of HEAD, or ``'unknown'`` outside a git checkout."""
    try:
        return subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return 'unknown'


def environment() -> dict:
    """Versions that have already changed a number on us once."""
    env = {'commit': git_sha()}
    for mod, key in (
        ('torch', 'torch'),
        ('transformers', 'transformers'),
        ('stable_pretraining', 'stable_pretraining'),
    ):
        try:
            env[key] = __import__(mod).__version__
        except Exception:  # noqa: BLE001 - a missing version is not fatal
            env[key] = 'unknown'
    try:
        import torch

        env['cuda'] = torch.version.cuda
        env['gpu'] = (
            torch.cuda.get_device_name(0)
            if torch.cuda.is_available()
            else 'cpu'
        )
    except Exception:  # noqa: BLE001 - reporting only
        env['cuda'] = env['gpu'] = 'unknown'
    return env


def parse_runs(path: Path) -> list[dict]:
    """Parse every CONFIG/RESULTS pair appended to one results file.

    Args:
        path: A results file written by ``eval_wm.py``.

    Returns:
        One dict per run, in file order, with the fields that identify the
        run and the numbers it produced.
    """
    text = path.read_text(encoding='utf-8')
    runs = []
    for block in text.split('==== CONFIG ====')[1:]:
        if '==== RESULTS ====' not in block:
            continue
        cfg_text, res_text = block.split('==== RESULTS ====', 1)
        cfg = yaml.safe_load(cfg_text)

        rate = re.search(r"'success_rate': ([0-9.]+)", res_text)
        elapsed = re.search(r'evaluation_time: ([0-9.]+)', res_text)
        successes = re.search(
            r"'episode_successes': array\(\[(.*?)\]\)", res_text, re.DOTALL
        )
        flags = []
        if successes:
            flags = [
                token == 'True'
                for token in re.findall(
                    r'\b(True|False)\b', successes.group(1)
                )
            ]

        runs.append(
            {
                'seed': cfg.get('seed'),
                'policy': cfg.get('policy'),
                'num_eval': cfg.get('eval', {}).get('num_eval'),
                'eval_budget': cfg.get('eval', {}).get('eval_budget'),
                'history_len': cfg.get('plan_config', {}).get('history_len'),
                'horizon': cfg.get('plan_config', {}).get('horizon'),
                'action_block': cfg.get('plan_config', {}).get('action_block'),
                'num_samples': cfg.get('solver', {}).get('num_samples'),
                'n_steps': cfg.get('solver', {}).get('n_steps'),
                'success_rate': float(rate.group(1)) if rate else None,
                'successes': sum(flags),
                'episodes': len(flags),
                'seconds': float(elapsed.group(1)) if elapsed else None,
            }
        )
    return runs


def render(runs: list[dict], env: dict, source: str, config_name: str) -> str:
    """Render the Markdown record."""
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    lines = [
        '# Eval results',
        '',
        f'Generated {stamp} by `scripts/collect_results.py`.',
        'Do not edit by hand; rerun the script instead.',
        '',
        f'Source: `{source}`',
        '',
        '## Environment',
        '',
        '| | |',
        '|---|---|',
    ]
    # The commit is HEAD *now*, not necessarily HEAD when the runs happened;
    # eval_wm.py does not record it, and that is upstream code. Label it so
    # nobody reads it as run provenance.
    labels = {'commit': 'commit (at collection)'}
    for key in ('commit', 'torch', 'cuda', 'gpu', 'transformers'):
        lines.append(f'| {labels.get(key, key)} | `{env.get(key)}` |')
    lines += [
        '',
        '## Runs',
        '',
        '| Policy | Seed | Horizon | Block | Episodes | Samples | CEM steps '
        '| Success | Seconds |',
        '|--------|------|---------|-------|----------|---------|-----------'
        '|---------|---------|',
    ]
    for r in runs:
        secs = f'{r["seconds"]:.0f}' if r['seconds'] else '-'
        # Horizon and action_block belong in the table: two runs that differ
        # only by horizon were otherwise indistinguishable here, and the
        # horizon turned out to be worth 45 points (README section 13).
        lines.append(
            f'| `{r["policy"]}` | {r["seed"]} | {r["horizon"]} '
            f'| {r["action_block"]} | {r["num_eval"]} '
            f'| {r["num_samples"]} | {r["n_steps"]} '
            f'| {r["successes"]}/{r["episodes"]} = {r["success_rate"]:.0f}% '
            f'| {secs} |'
        )

    # Summarise only the runs that used the full protocol; smoke tests would
    # drag the mean down and they are not comparable to anything.
    full = [
        r
        for r in runs
        if r['num_eval'] == 50
        and r['num_samples'] == 300
        and r['n_steps'] == 30
    ]
    if len(full) > 1:
        rates = [r['success_rate'] for r in full]
        pooled_ok = sum(r['successes'] for r in full)
        pooled_n = sum(r['episodes'] for r in full)
        lines += [
            '',
            '## Full-protocol summary',
            '',
            f'{len(full)} runs at 50 episodes, 300 samples, 30 CEM steps.',
            '',
            '| | |',
            '|---|---|',
            f'| Mean | {statistics.mean(rates):.1f}% |',
            f'| Std | {statistics.stdev(rates):.1f} |',
            f'| Range | {min(rates):.0f}% to {max(rates):.0f}% |',
            f'| Pooled | {pooled_ok}/{pooled_n} = {100 * pooled_ok / pooled_n:.1f}% |',
        ]

    # Derived from the runs themselves. This used to be a hardcoded LeWM
    # command, so every record claimed LeWM produced it, whatever the policy.
    seeds = ','.join(str(s) for s in sorted({r['seed'] for r in runs}))
    lines += [
        '',
        '## Commands',
        '',
        'Reproduce these runs with:',
        '',
        '```bash',
    ]
    for policy in sorted({r['policy'] for r in runs}):
        lines += [
            f'python scripts/plan/eval_wm.py --config-name {config_name} -m \\',
            f'    policy={policy} seed={seeds}',
        ]
    lines += ['```', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--results-file',
        default='inzva_pusht_results.txt',
        help='filename written by eval_wm.py (output.filename)',
    )
    parser.add_argument(
        '--policy-dir',
        default='quentinll',
        help='subdirectory of checkpoints/ holding the results file',
    )
    parser.add_argument(
        '--config-name',
        default='inzva_pusht',
        help='eval config the runs used; only written into the Commands section',
    )
    parser.add_argument('--out', default=str(DEFAULT_OUT))
    args = parser.parse_args()

    home = os.environ.get('STABLEWM_HOME')
    if not home:
        raise SystemExit(
            'STABLEWM_HOME is not set; see INZVA_README.md section 3'
        )
    source = Path(home) / 'checkpoints' / args.policy_dir / args.results_file
    if not source.exists():
        raise SystemExit(f'no results file at {source}')
    # Record the path relative to STABLEWM_HOME so the tracked file is the
    # same on every machine and diffs stay readable.
    # normpath, because a policy id with no owner passes --policy-dir . and
    # would otherwise record checkpoints/./<file>.
    portable = '$STABLEWM_HOME/' + posixpath.normpath(
        f'checkpoints/{args.policy_dir}/{args.results_file}'
    )

    runs = parse_runs(source)
    if not runs:
        raise SystemExit(f'{source} contained no parseable runs')
    env = environment()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.results_file).stem

    # newline='\n' so these land as LF on every platform, matching the
    # normalisation in .gitattributes. Without it Windows writes CRLF and every
    # regenerated record shows up as modified until git rewrites it.
    md = out_dir / f'{stem}.md'
    md.write_text(
        render(runs, env, portable, args.config_name),
        encoding='utf-8',
        newline='\n',
    )

    js = out_dir / f'{stem}.json'
    js.write_text(
        json.dumps(
            {
                'generated': datetime.now(timezone.utc).isoformat(),
                'source': portable,
                'environment': env,
                'runs': runs,
            },
            indent=2,
        )
        # json.dumps omits the trailing newline, which trips the repo's
        # end-of-file-fixer pre-commit hook and fails CI.
        + '\n',
        encoding='utf-8',
        newline='\n',
    )

    print(f'parsed {len(runs)} run(s) from {source}')
    for r in runs:
        print(
            f'  seed {r["seed"]:>3}  {r["num_eval"]:>3} eps  '
            f'{r["success_rate"]:.0f}%'
        )
    print(f'wrote {md}')
    print(f'wrote {js}')


if __name__ == '__main__':
    main()
