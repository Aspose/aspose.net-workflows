"""
Compare normalize-report.json against stored baseline.
Flags: any defect class count >2x baseline, or new class appearing at >50.
Exit code 0 = OK, 1 = anomaly.

Usage: python tests/check_report_anomaly.py <report.json>
"""
import json
import sys
import os


def check(report_path, baseline_path):
    with open(report_path) as f:
        report = json.load(f)
    if not os.path.exists(baseline_path):
        print('[WARN] No baseline file found. Skipping anomaly check.')
        return
    with open(baseline_path) as f:
        baseline = json.load(f)

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
        print('If expected (new package version), update tests/baselines/normalize_baseline.json.')
        sys.exit(1)
    else:
        print('[OK] Defect counts within expected range.')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: check_report_anomaly.py <report.json>')
        sys.exit(1)
    baseline_path = os.path.join(os.path.dirname(__file__), 'baselines', 'normalize_baseline.json')
    check(sys.argv[1], baseline_path)
