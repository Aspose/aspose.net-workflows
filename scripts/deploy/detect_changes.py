"""
Detect content changes in the Aspose/aspose.net repo and map them to workflow filenames.

Usage:
    python detect_changes.py <content_repo_path> <last_scanned_sha> [--manifest <path>]

If last_scanned_sha is empty, all deploy workflows are returned (initial run).

Outputs (written to GITHUB_OUTPUT if available):
    workflows     - JSON array of workflow filenames to trigger
    has_changes   - "true" or "false"
    new_sha       - HEAD SHA of the content repo
    global_change - "true" or "false"

If --manifest is provided, writes a deploy_manifest.json at the given path.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# --- Mapping Configuration ---

FAMILY_SECTIONS = {
    "products.aspose.net": [
        "barcode", "cad", "cells", "email", "home", "html", "imaging",
        "medical", "ocr", "page", "pdf", "psd", "slides", "svg",
        "tasks", "tex", "words", "zip",
    ],
    "docs.aspose.net": [
        "barcode", "cad", "cells", "email", "file-formats", "home",
        "html", "imaging", "medical", "ocr", "page", "pdf", "psd",
        "slides", "tasks", "tex", "words", "zip",
    ],
    "kb.aspose.net": [
        "barcode", "cells", "email", "home", "html", "imaging",
        "medical", "ocr", "page", "pdf", "psd", "slides", "tasks",
        "tex", "words", "zip",
    ],
    "reference.aspose.net": [
        "barcode", "cad", "cells", "email", "home", "html", "imaging",
        "medical", "note", "ocr", "page", "pdf", "slides", "svg",
        "tasks", "tex", "words", "zip",
    ],
}

WHOLE_SECTIONS = [
    "blog.aspose.net",
    "www.aspose.net",
    "about.aspose.net",
    "websites.aspose.net",
]

# Paths outside content/ that affect all sites (theme, layout, static assets)
GLOBAL_PATHS = ["themes/", "layouts/", "archetypes/", "static/", "i18n/"]


def get_all_deploy_workflows():
    """Return the full list of every deploy workflow filename."""
    workflows = set()
    for section, families in FAMILY_SECTIONS.items():
        for family in families:
            workflows.add(f"{section}-{family}.yml")
    for section in WHOLE_SECTIONS:
        workflows.add(f"{section}.yml")
    return workflows


def map_path_to_workflow(path):
    """
    Map a single changed file path to zero or more workflow filenames.
    Returns (set_of_workflows, is_global_change).
    """
    workflows = set()
    parts = path.replace("\\", "/").split("/")

    # Check for global paths (themes, layouts, etc.)
    for gp in GLOBAL_PATHS:
        if path.startswith(gp):
            return get_all_deploy_workflows(), True

    # content/<section>/<family>/... or content/<section>/...
    if len(parts) >= 2 and parts[0] == "content":
        section = parts[1]

        if section in FAMILY_SECTIONS and len(parts) >= 3:
            family = parts[2]
            if family in FAMILY_SECTIONS[section]:
                workflows.add(f"{section}-{family}.yml")
            else:
                # Changed file is directly under content/<section>/ (not in a known family)
                # Could be a shared file for the section — trigger home
                workflows.add(f"{section}-home.yml")
        elif section in WHOLE_SECTIONS:
            workflows.add(f"{section}.yml")

    # configs/<section>/<family>.toml or configs/<section>.toml/.yml
    if len(parts) >= 2 and parts[0] == "configs":
        if len(parts) == 3:
            # configs/<section>/<family>.toml
            section = parts[1]
            family_file = parts[2]
            family = family_file.rsplit(".", 1)[0]  # strip extension
            if section in FAMILY_SECTIONS and family in FAMILY_SECTIONS[section]:
                workflows.add(f"{section}-{family}.yml")
        elif len(parts) == 2:
            # configs/<section>.toml or configs/<section>.yml
            config_file = parts[1]
            section = config_file.rsplit(".", 1)[0]  # strip extension
            if section in WHOLE_SECTIONS:
                workflows.add(f"{section}.yml")

    return workflows, False


def add_home_workflows(workflows):
    """
    If any family workflow for a section is triggered, also trigger
    the section's home workflow (home pages aggregate family data).
    """
    sections_with_changes = set()
    for wf in list(workflows):
        for section in FAMILY_SECTIONS:
            if wf.startswith(f"{section}-") and wf != f"{section}-home.yml":
                sections_with_changes.add(section)

    for section in sections_with_changes:
        home_wf = f"{section}-home.yml"
        if home_wf not in workflows:
            workflows.add(home_wf)

    return workflows


def get_changed_files(repo_path, last_sha):
    """Get list of changed files between last_sha and HEAD."""
    if not last_sha:
        # First run: return empty to trigger all workflows
        return None

    result = subprocess.run(
        ["git", "diff", "--name-only", f"{last_sha}..HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"ERROR: git diff failed: {result.stderr}", file=sys.stderr)
        # On error, treat as initial run (deploy all)
        return None

    files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    return files


def get_head_sha(repo_path):
    """Get the current HEAD SHA of the content repo."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: git rev-parse failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def write_github_output(key, value):
    """Write a key=value pair to GITHUB_OUTPUT if available."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{key}={value}\n")
    # Also print for local debugging
    print(f"  {key}={value}")


def write_manifest(path, workflow_list, new_sha, last_sha, global_change):
    """Write the deploy manifest JSON file."""
    manifest = {
        "scan_id": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"),
        "content_sha": new_sha,
        "previous_sha": last_sha,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "global_change": global_change,
        "affected_workflows": workflow_list,
        "staging_status": "pending",
        "production_status": "pending",
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest written to: {path}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python detect_changes.py <content_repo_path> <last_sha> [--manifest <path>]")
        sys.exit(1)

    repo_path = sys.argv[1]
    last_sha = sys.argv[2].strip()

    manifest_path = None
    if "--manifest" in sys.argv:
        idx = sys.argv.index("--manifest")
        if idx + 1 < len(sys.argv):
            manifest_path = sys.argv[idx + 1]

    new_sha = get_head_sha(repo_path)
    print(f"Content repo HEAD: {new_sha}")
    print(f"Last scanned SHA:  {last_sha or '(none — initial run)'}")

    changed_files = get_changed_files(repo_path, last_sha)

    if changed_files is None:
        # Initial run or error — deploy everything
        print("Initial run or git diff error: triggering all deploy workflows")
        workflows = get_all_deploy_workflows()
        global_change = True
    elif not changed_files:
        # No changes
        print("No changes detected since last scan.")
        write_github_output("has_changes", "false")
        write_github_output("workflows", "[]")
        write_github_output("new_sha", new_sha)
        write_github_output("global_change", "false")
        return
    else:
        print(f"Changed files ({len(changed_files)}):")
        for f in changed_files[:50]:  # Print first 50
            print(f"  - {f}")
        if len(changed_files) > 50:
            print(f"  ... and {len(changed_files) - 50} more")

        workflows = set()
        global_change = False

        for filepath in changed_files:
            mapped, is_global = map_path_to_workflow(filepath)
            workflows.update(mapped)
            if is_global:
                global_change = True

        if global_change:
            workflows = get_all_deploy_workflows()

        workflows = add_home_workflows(workflows)

    workflow_list = sorted(workflows)

    print(f"\nWorkflows to trigger ({len(workflow_list)}):")
    for wf in workflow_list:
        print(f"  -> {wf}")

    has_changes = "true" if workflow_list else "false"

    write_github_output("has_changes", has_changes)
    write_github_output("workflows", json.dumps(workflow_list))
    write_github_output("new_sha", new_sha)
    write_github_output("global_change", str(global_change).lower())

    if manifest_path and workflow_list:
        write_manifest(manifest_path, workflow_list, new_sha, last_sha, global_change)


if __name__ == "__main__":
    main()
