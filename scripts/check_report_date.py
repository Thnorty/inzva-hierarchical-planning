"""Fail a commit that edits the status page without touching its date.

Team rule 5 (INZVA_README.md) says the status page ships with the work. The
part that slipped anyway was its own header: the page said "updated 18
September" for two days after it was last edited, because updating prose and
updating the date are separate acts and only one of them is obvious.

This runs as a pre-commit hook. It only complains when the page is actually
being committed, so a full-repo run on an untouched file passes and CI stays
green on days nobody edits it.

    python scripts/check_report_date.py notes/inzva-progress.html
"""

import re
import subprocess
import sys
from datetime import date

# "13 September 2026, updated 20 September" in the facts list, and
# "last updated 20 September 2026" in the footer.
UPDATED = re.compile(r'updated\s+(\d{1,2})\s+([A-Z][a-z]+)')

MONTHS = {
    'January': 1,
    'February': 2,
    'March': 3,
    'April': 4,
    'May': 5,
    'June': 6,
    'July': 7,
    'August': 8,
    'September': 9,
    'October': 10,
    'November': 11,
    'December': 12,
}


NAMES = {number: name for name, number in MONTHS.items()}


def staged_files() -> set[str]:
    out = subprocess.run(
        ['git', 'diff', '--cached', '--name-only'],
        capture_output=True,
        text=True,
        check=False,
    )
    return {line.strip() for line in out.stdout.splitlines() if line.strip()}


def main(paths: list[str]) -> int:
    staged = staged_files()
    # %-d is a glibc extension that raises on Windows, so the day is
    # formatted separately from the month name.
    today = date.today()
    failed = False

    for path in paths:
        # Nothing staged means a full-repo run (CI, or `--all-files`), where
        # the date is allowed to be as old as the last real edit.
        if path.replace('\\', '/') not in staged:
            continue

        text = open(path, encoding='utf-8').read()
        found = {
            (int(day), MONTHS[month])
            for day, month in UPDATED.findall(text)
            if month in MONTHS
        }
        if not found:
            print(f'{path}: no "updated <day> <Month>" line to check')
            failed = True
            continue

        stale = [
            f'{d} {NAMES[m]}'
            for d, m in sorted(found)
            if (m, d) != (today.month, today.day)
        ]
        if stale:
            print(
                f'{path}: says updated {", ".join(stale)} but is being '
                f'committed on {today.day} {today:%B}.\n'
                '  Update the date in the facts list and the footer. '
                'See team rule 5 in INZVA_README.md.'
            )
            failed = True

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
