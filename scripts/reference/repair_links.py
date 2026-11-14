#!/usr/bin/env python3
"""Repair internal links on ALREADY GENERATED reference pages (English and locale copies).

Runs the same logic as the generator's post-processor (link_fixer.py) over existing page folders, so
pages generated before the anchored-link fix (and locale copies, which the generator does not
regenerate) can be repaired mechanically. Dry run by default: nothing is written without ``--apply``.

Usage:
  python scripts/reference/repair_links.py --root <content/reference.aspose.net/pdf> --family pdf \
      --family-name Aspose.PDF --xml <Aspose.PDF.xml> [--repair-extra] [--apply] [--report report.json]

``--root`` may be a single page folder (``.../pdf/en``) or the family folder that contains one folder per
language (``.../pdf``). Every folder that directly contains ``*.md`` pages is processed on its own.

Checks (always run; a failing check makes the exit code 1):
  * only link targets changed (all other text is byte-identical),
  * every rewritten anchored link lands on an existing page and an existing ``<a id="...">`` anchor,
  * a second pass over the result changes nothing (idempotent).
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import link_fixer  # noqa: E402

_TARGET_RE = re.compile(r"\]\([^)]*\)")
_ANCHOR_LINK_RE = re.compile(r"\]\(/([^/)#]+)/([^/)#]+)/#([^)]*)\)")
_ID_RE = re.compile(r'<a id="([^"]+)"')


def _page_dirs(root):
    if any(f.endswith(".md") for f in os.listdir(root)):
        yield root
    for name in sorted(os.listdir(root)):
        sub = os.path.join(root, name)
        if os.path.isdir(sub) and any(f.endswith(".md") for f in os.listdir(sub)):
            yield sub


def _read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _mask_targets(text):
    """Replace every markdown link target by a constant: equal masks mean only link targets differ."""
    return _TARGET_RE.sub("](X)", text)


def run(root, family, family_name, xml_path, repair_extra, apply_changes):
    type_index = None
    if xml_path:
        type_index = link_fixer.TypeIndex.from_xml_text(open(xml_path, encoding="utf-8", errors="replace").read())
    if repair_extra and type_index is None:
        print("Note: no --xml given; links to missing pages are counted as unresolved, not rewritten.", file=sys.stderr)

    report = {"root": root, "apply": apply_changes, "repair_extra": repair_extra, "folders": {}, "totals": Counter(), "problems": []}
    for folder in _page_dirs(root):
        files = sorted(f for f in os.listdir(folder) if f.endswith(".md"))
        overview = family_name.lower()
        pages = {f[:-3].lower() for f in files} - {"_index", overview}
        ids = {}  # lowercase slug -> set of anchors (lazy)
        stats = Counter()
        changed, unresolved_dangling = [], Counter()
        results = {}
        for fn in files:
            path = os.path.join(folder, fn)
            old = _read(path)
            file_stats = {}
            new = link_fixer.rewrite_internal_links(
                old, family, family_name, existing_pages=pages, type_index=type_index,
                overview_slug=overview, repair_extra=repair_extra, stats=file_stats,
            )
            for k, v in file_stats.items():
                stats[k] += v
            if new != old:
                if _mask_targets(new) != _mask_targets(old):
                    report["problems"].append(f"{folder}/{fn}: text outside link targets changed")
                again = link_fixer.rewrite_internal_links(
                    new, family, family_name, existing_pages=pages, type_index=type_index,
                    overview_slug=overview, repair_extra=repair_extra, stats={},
                )
                if again != new:
                    report["problems"].append(f"{folder}/{fn}: second pass is not a no-op")
                changed.append(fn)
                results[fn] = new
            else:
                results[fn] = old
            if file_stats.get("dangling_unresolved"):
                for m in re.finditer(rf"\]\(/{re.escape(family)}/([^)#/\s]+)", new):
                    s = m.group(1).lower()
                    if s not in pages:
                        unresolved_dangling[s] += 1

        # Verify rewritten anchored links against the pages that exist in this folder.
        by_slug = {f[:-3].lower(): f for f in files}
        anchored_checked = anchored_bad = 0
        for fn in changed:
            for m in _ANCHOR_LINK_RE.finditer(results[fn]):
                if m.group(1) != family:
                    continue
                slug, anchor = m.group(2).lower(), m.group(3)
                anchored_checked += 1
                target = by_slug.get(slug)
                if target is None:
                    anchored_bad += 1
                    report["problems"].append(f"{folder}/{fn}: anchored link to missing page {slug}")
                    continue
                if slug not in ids:
                    ids[slug] = set(_ID_RE.findall(results[target]))
                if anchor not in ids[slug]:
                    anchored_bad += 1
                    report["problems"].append(f"{folder}/{fn}: anchor #{anchor} not found in {target}")

        if apply_changes:
            for fn in changed:
                with open(os.path.join(folder, fn), "w", encoding="utf-8", newline="") as f:
                    f.write(results[fn])

        report["folders"][folder] = {
            "files": len(files), "files_changed": len(changed), "anchored_rewritten": stats["anchored"],
            "plain_rewritten": stats["plain"], "dangling_rewritten": stats["dangling_rewritten"],
            "overview_to_root": stats["overview_to_root"], "external_unescaped": stats["external_unescaped"],
            "dangling_unresolved": stats["dangling_unresolved"], "unresolved_slugs": dict(unresolved_dangling),
            "anchored_checked": anchored_checked, "anchored_bad": anchored_bad,
        }
        for k in ("files", "files_changed", "anchored_rewritten", "plain_rewritten", "dangling_rewritten",
                  "overview_to_root", "external_unescaped", "dangling_unresolved", "anchored_checked", "anchored_bad"):
            report["totals"][k] += report["folders"][folder][k]
    report["totals"] = dict(report["totals"])
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", required=True)
    ap.add_argument("--family", required=True, help="lowercase family key used in URLs, e.g. pdf")
    ap.add_argument("--family-name", required=True, help="package family name, e.g. Aspose.PDF")
    ap.add_argument("--xml", help="package XML documentation (for the type list used by --dangling)")
    ap.add_argument("--repair-extra", "--dangling", dest="repair_extra", action="store_true",
                    help="also rewrite links to pages that do not exist, links to the overview page and escaped absolute URLs")
    ap.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    ap.add_argument("--report", help="write the JSON report here")
    a = ap.parse_args()
    rep = run(a.root, a.family, a.family_name, a.xml, a.repair_extra, a.apply)
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, ensure_ascii=False)
    print(json.dumps({"totals": rep["totals"], "problems": rep["problems"][:20], "n_problems": len(rep["problems"])}, indent=2))
    return 1 if rep["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
