"""
Compare normalize-report.json against stored baseline.
Flags: any defect class count >2x baseline, or new class appearing at >50.
Exit code 0 = OK, 1 = anomaly.

Baseline resolution order:
  1. tests/baselines/<family>.json  (e.g. words.json for Aspose.Words)
  2. tests/baselines/normalize_baseline.json  (global fallback)
  3. No baseline found → warning + exit 0 (non-blocking)

Usage:
  python tests/check_report_anomaly.py <report.json> [--family <name>]

  <name> is the short family name, case-insensitive (e.g. 'words', 'Aspose.Words').
  'Aspose.' prefix is stripped automatically.
"""
import json
import sys
import os


def _resolve_baseline(baselines_dir, family):
    """Return the best-matching baseline path for the given family (or None)."""
    if family:
        short = family.lower().removeprefix('aspose.')
        candidate = os.path.join(baselines_dir, f'{short}.json')
        if os.path.exists(candidate):
            return candidate
    global_path = os.path.join(baselines_dir, 'normalize_baseline.json')
    return global_path if os.path.exists(global_path) else None


def check(report_path, baselines_dir, family=None):
    with open(report_path) as f:
        report = json.load(f)

    baseline_path = _resolve_baseline(baselines_dir, family)
    if not baseline_path:
        print('[WARN] No baseline file found. Skipping anomaly check.')
        return

    with open(baseline_path) as f:
        baseline = json.load(f)

    label = os.path.basename(baseline_path)
    print(f'[INFO] Using baseline: {label}')

    counts = report.get('defect_counts', {})
    base = baseline.get('defect_counts', {})
    anomalies = []

    for cls, count in counts.items():
        base_count = base.get(cls, 0)
        if base_count == 0 and count > 50:
            anomalies.append(f'NEW class {cls}: {count} occurrences (threshold: >50)')
        elif base_count > 0 and count > base_count * 2:
            anomalies.append(f'Class {cls}: {count} vs baseline {base_count} (>2x increase)')

    if anomalies:
        print('[ANOMALY] Defect count anomalies detected:')
        for a in anomalies:
            print(f'  - {a}')
        print(f'If expected, update tests/baselines/{label}.')
        sys.exit(1)
    else:
        print('[OK] Defect counts within expected range.')


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print('Usage: check_report_anomaly.py <report.json> [--family <name>]')
        sys.exit(1)
    report_arg = args[0]
    family_arg = None
    if '--family' in args:
        idx = args.index('--family')
        if idx + 1 < len(args):
            family_arg = args[idx + 1]
    baselines_dir = os.path.join(os.path.dirname(__file__), 'baselines')
    check(report_arg, baselines_dir, family_arg)
