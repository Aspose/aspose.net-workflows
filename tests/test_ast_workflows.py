"""
Structural regression tests for the AST locale workflows
(ast-creator.yml, ast-translator.yml, ast2md-converter.yml).

These guard the defects found when the locale pipeline was first run for the
pdf reference pages:

  * ast-creator passed `--families` (not an option of ast-creator.py) and tried
    to push the gitignored /ast folder
  * ast-translator passed an AST *folder* where ast-translator.py needs the
    nodes.txt produced by ast-filter.py, never installed `accelerate`, and was
    limited to a hardcoded list of 20 languages
  * ast2md-converter pushed straight to main, never pruned stale pages and was
    limited to the same hardcoded 20 languages

Run with: python -m pytest tests/test_ast_workflows.py -v
"""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
OLD_HARDCODED = "de,es,fr,ja,ko,ru,zh,ar,it,pt,pl,fa,id,cs,vi,tr,th,sv,el,uk"


def _text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def _load(name: str) -> dict:
    return yaml.safe_load(_text(name))


def _triggers(doc: dict) -> dict:
    # PyYAML parses the bare key `on` as boolean True
    return doc.get("on") or doc.get(True)


@pytest.mark.parametrize("name", ["ast-creator.yml", "ast-translator.yml", "ast2md-converter.yml"])
def test_workflow_parses_and_keeps_both_triggers(name):
    on = _triggers(_load(name))
    assert "workflow_dispatch" in on and "workflow_call" in on


@pytest.mark.parametrize("name", ["ast-creator.yml", "ast-translator.yml", "ast2md-converter.yml"])
def test_no_hardcoded_language_list(name):
    assert OLD_HARDCODED not in _text(name)


@pytest.mark.parametrize("name", ["ast-translator.yml", "ast2md-converter.yml"])
def test_languages_default_to_auto_derived_from_repo(name):
    on = _triggers(_load(name))
    for trigger in ("workflow_dispatch", "workflow_call"):
        lang = on[trigger]["inputs"]["languages"]
        assert lang["default"] == "auto"
        assert lang.get("required") in (False, None)
    assert "list_locales.py" in _text(name)


def test_creator_uses_a_supported_option_and_does_not_push_ast():
    text = _text("ast-creator.yml")
    assert "--families" not in text, "ast-creator.py only knows --input/--subdomain/--family"
    assert "git push" not in text and "git add" not in text, "/ast is gitignored derived data"
    assert "scripts/ast-translator/ast-creator.py --input" in text


def test_translator_feeds_nodes_txt_to_the_translator():
    text = _text("ast-translator.yml")
    assert "ast-filter.py" in text
    assert re.search(r"ast-translator\.py[^\n]*\\\n\s+--input aspose-net/scripts/ast-translator/nodes\.txt", text)
    assert "accelerate" in text, "ast-translator.py imports accelerate at module level"


def test_translator_does_not_use_the_workflow_ref_as_the_cache_branch():
    text = _text("ast-translator.yml")
    assert "GITHUB_REF#refs/heads/" not in text
    assert "TC_BRANCH" in text


def test_ast2md_delivers_by_pull_request_never_by_pushing_to_main():
    text = _text("ast2md-converter.yml")
    assert "gh pr create" in text
    assert "git push origin HEAD" not in text
    assert re.search(r"git push origin \"\$BRANCH\"", text)


def test_ast2md_branch_cannot_trigger_the_auto_merge_workflow():
    # Aspose/aspose.net auto-merges branches starting with these prefixes.
    m = re.search(r'BRANCH="([^"$]*)', _text("ast2md-converter.yml"))
    assert m, "branch name not found"
    assert not m.group(1).startswith(("api-update-", "optimizer-"))


def test_ast2md_prunes_stale_pages_for_reference_and_stages_deletions():
    text = _text("ast2md-converter.yml")
    assert "--prune" in text and "reference.aspose.net" in text
    assert "git add -A -- " in text, "pruned pages are deletions and must be staged"
    assert "git add -f content/*.md" not in text


def test_ast2md_does_not_deep_clone_the_cache_repo():
    steps = _load("ast2md-converter.yml")["jobs"]["generate_markdown"]["steps"]
    cache = next(s for s in steps if s.get("with", {}).get("repository") == "smallize/translationcache")
    assert cache["with"]["fetch-depth"] == 1
