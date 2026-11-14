"""
Tests for the reference link fix: scripts/reference/link_fixer.py, repair_links.py and the wiring in
postprocessor.py.

Run with: python -m pytest tests/test_reference_postprocessor.py -v

Fixtures in tests/fixtures/reference_links/ are real generated pages (Aspose.PDF LowCode, one German
locale copy, and one page each from diagram, cells, words and cad) plus a minimal package-XML type list.
"""
import os
import random
import re
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts", "reference")
FIX = os.path.join(HERE, "fixtures", "reference_links")
sys.path.insert(0, SCRIPTS)

import link_fixer  # noqa: E402
import repair_links  # noqa: E402


def read(*parts):
    with open(os.path.join(FIX, *parts), encoding="utf-8", newline="") as f:
        return f.read()


def targets(text):
    return re.findall(r"\]\(([^)]*)\)", text)


def mask(text):
    return re.sub(r"\]\([^)]*\)", "](X)", text)


def legacy_process_internal_links(content, family, family_name):
    """The implementation before this fix, verbatim (postprocessor.py process_internal_links)."""
    content = re.sub(
        rf'Namespace: \[{re.escape(family_name)}\]\(\s*{re.escape(family_name)}\.md\s*\)',
        f'Namespace: [{family_name}](/{family}/)',
        content,
    )
    content = re.sub(
        r'\[([^\]]+)\]\((?!https?://)([^)]+\.md)\)',
        lambda m: f"[{m.group(1)}](/{family}/{m.group(2).lower().replace('.md', '').lstrip('/')})"
        if not m.group(2).lower().startswith(family)
        else f"[{m.group(1)}](/" + m.group(2).lower().replace('.md', '').lstrip('/') + ")",
        content,
    )
    return content


PDF_PAGES = {
    "aspose.pdf.lowcode", "aspose.pdf.lowcode.compressoptions", "aspose.pdf.lowcode.organizerbaseoptions",
    "aspose.pdf.lowcode.idatasource", "aspose.pdf.lowcode.ipluginoptions", "aspose.pdf.lowcode.pdfaoptionsbase",
    "aspose.pdf.lowcode.pdfaconvertoptions", "aspose.pdf.lowcode.pdfastandardversion",
    "aspose.pdf.lowcode.pdfavalidateoptions",
}


@pytest.fixture(scope="module")
def type_index():
    return link_fixer.TypeIndex.from_xml_text(read("types.xml"))


# ---------------------------------------------------------------------------
# Anchored links (the defect)
# ---------------------------------------------------------------------------

class TestAnchoredLinks:

    def test_escaped_anchor_is_rewritten(self):
        out = link_fixer.rewrite_internal_links(read("pdf_en", "Aspose.Pdf.LowCode.CompressOptions.md"), "pdf", "Aspose.PDF")
        assert (
            "[OrganizerBaseOptions.Inputs](/pdf/aspose.pdf.lowcode.organizerbaseoptions/"
            "#Aspose_Pdf_LowCode_OrganizerBaseOptions_Inputs)" in out
        )

    def test_no_raw_md_or_backslash_targets_remain(self):
        out = link_fixer.rewrite_internal_links(read("pdf_en", "Aspose.Pdf.LowCode.CompressOptions.md"), "pdf", "Aspose.PDF")
        for t in targets(out):
            assert ".md" not in t and "\\" not in t, t

    def test_link_text_with_escaped_parentheses_is_untouched(self):
        out = link_fixer.rewrite_internal_links(read("pdf_en", "Aspose.Pdf.LowCode.CompressOptions.md"), "pdf", "Aspose.PDF")
        assert r"[OrganizerBaseOptions.AddInput\(IDataSource\)](" in out

    def test_old_code_leaves_the_defect(self):
        """Documents the bug this fix removes: the legacy regex never touched anchored links."""
        src = read("pdf_en", "Aspose.Pdf.LowCode.CompressOptions.md")
        legacy = legacy_process_internal_links(src, "pdf", "Aspose.PDF")
        assert ".md\\#" in legacy

    def test_locale_form_without_backslashes(self):
        """Locale copies carry File.md#Anchor (the AST round trip strips the backslashes)."""
        de = read("pdf_de", "Aspose.Pdf.LowCode.CompressOptions.md")
        assert re.search(r"\]\([A-Za-z.]+\.md#", de)
        out = link_fixer.rewrite_internal_links(de, "pdf", "Aspose.PDF")
        for t in targets(out):
            assert ".md" not in t, t
        en_out = link_fixer.rewrite_internal_links(read("pdf_en", "Aspose.Pdf.LowCode.CompressOptions.md"), "pdf", "Aspose.PDF")
        anchored = lambda s: {t for t in targets(s) if "/#" in t}
        assert anchored(out) == anchored(en_out) and anchored(out)

    def test_every_rewritten_anchor_exists_in_the_target_page(self):
        out = link_fixer.rewrite_internal_links(read("pdf_en", "Aspose.Pdf.LowCode.CompressOptions.md"), "pdf", "Aspose.PDF")
        ids = set(re.findall(r'<a id="([^"]+)"', read("pdf_en", "Aspose.Pdf.LowCode.OrganizerBaseOptions.md")))
        links = [t for t in targets(out) if "/#" in t]
        assert links
        for t in links:
            page, anchor = t.rsplit("/#", 1)
            assert page == "/pdf/aspose.pdf.lowcode.organizerbaseoptions"
            assert anchor in ids, anchor

    def test_anchor_case_is_preserved(self):
        out = link_fixer.rewrite_internal_links("[a](Foo.Bar.md\\#Foo\\_Bar\\_Baz)", "pdf", "Aspose.PDF")
        assert out == "[a](/pdf/foo.bar/#Foo_Bar_Baz)"

    def test_escaped_hyphen_in_generic_page_name(self):
        """DocFX escapes '-' in generic type pages (CadParameter\\-1.md)."""
        src = read("other", "cad_CadBinaryParameter.md")
        assert "\\-1.md" in src
        out = link_fixer.rewrite_internal_links(src, "cad", "Aspose.CAD")
        generic = [t for t in targets(out) if "cadparameter-1" in t]
        assert generic and all("\\" not in t and ".md" not in t for t in generic)
        internal = [t for t in targets(out) if t.startswith("/cad/")]
        assert internal and all("\\" not in t for t in internal)

    @pytest.mark.parametrize("name,family,family_name", [
        ("pdf_en/Aspose.Pdf.LowCode.CompressOptions.md", "pdf", "Aspose.PDF"),
        ("pdf_en/Aspose.Pdf.LowCode.OrganizerBaseOptions.md", "pdf", "Aspose.PDF"),
        ("pdf_en/Aspose.Pdf.LowCode.PdfAOptionsBase.md", "pdf", "Aspose.PDF"),
        ("pdf_de/Aspose.Pdf.LowCode.CompressOptions.md", "pdf", "Aspose.PDF"),
        ("other/diagram_LowCodePdfSaveOptions.md", "diagram", "Aspose.Diagram"),
        ("other/cells_LowCodePdfSaveOptions.md", "cells", "Aspose.Cells"),
        ("other/words_Zip64Mode.md", "words", "Aspose.Words"),
        ("other/cad_CadBinaryParameter.md", "cad", "Aspose.CAD"),
    ])
    def test_only_link_targets_change_and_second_pass_is_a_noop(self, name, family, family_name):
        src = read(*name.split("/"))
        out = link_fixer.rewrite_internal_links(src, family, family_name)
        assert mask(out) == mask(src)  # nothing but link targets differs
        again = link_fixer.rewrite_internal_links(out, family, family_name)
        assert again == out

    def test_other_families_only_gain_the_anchored_rewrite(self):
        """With dangling rewrite off (the default) a non-pdf page changes only where it had an anchored .md link."""
        for name, family, family_name in [
            ("other/diagram_LowCodePdfSaveOptions.md", "diagram", "Aspose.Diagram"),
            ("other/cells_LowCodePdfSaveOptions.md", "cells", "Aspose.Cells"),
            ("other/words_Zip64Mode.md", "words", "Aspose.Words"),
        ]:
            src = read(*name.split("/"))
            legacy = legacy_process_internal_links(src, family, family_name)
            new = link_fixer.rewrite_internal_links(src, family, family_name)
            changed_old = [t for t in targets(src) if ".md" in t]
            assert legacy == src  # the pages are already post-processed: legacy was a no-op on them
            for t in targets(new):
                assert t in targets(src) or t.startswith(f"/{family}/")
            assert len(targets(new)) == len(targets(src))
            assert (new != src) == bool(changed_old)


# ---------------------------------------------------------------------------
# Non-anchored links: behaviour must be exactly the legacy behaviour
# ---------------------------------------------------------------------------

class TestPlainLinksUnchanged:

    @pytest.mark.parametrize("text", [
        "[Foo](Aspose.Pdf.Foo.md)",
        "[Foo](/Aspose.Pdf.Foo.md)",
        "[Foo](Aspose.Pdf.Foo.MD)",
        "[Foo](pdf.something.md)",              # target already starts with the family name
        "[Foo](https://example.com/a.md)",       # absolute links are never touched
        "Namespace: [Aspose.PDF](Aspose.PDF.md)",
        "Namespace: [Aspose.PDF]( Aspose.PDF.md )",
        "see [a](A.md) and [b](B.md) and [c](https://x.y/z)",
        "[no link](just text)",
    ])
    def test_matches_legacy(self, text):
        assert link_fixer.rewrite_internal_links(text, "pdf", "Aspose.PDF") == legacy_process_internal_links(text, "pdf", "Aspose.PDF")

    def test_fuzz_matches_legacy(self):
        rnd = random.Random(1234)
        words = ["Aspose", "Pdf", "LowCode", "Foo", "BarBaz", "pdf", "x1", "Opt-1"]
        for _ in range(400):
            path = ".".join(rnd.choice(words) for _ in range(rnd.randint(1, 4))) + ".md"
            if rnd.random() < 0.2:
                path = "/" + path
            text = f"prefix [{rnd.choice(words)}]({path}) suffix"
            assert link_fixer.rewrite_internal_links(text, "pdf", "Aspose.PDF") == legacy_process_internal_links(text, "pdf", "Aspose.PDF"), text

    def test_namespace_line(self):
        out = link_fixer.rewrite_internal_links("Namespace: [Aspose.PDF](Aspose.PDF.md)", "pdf", "Aspose.PDF")
        assert out == "Namespace: [Aspose.PDF](/pdf/)"


# ---------------------------------------------------------------------------
# Dangling links (opt-in)
# ---------------------------------------------------------------------------

class TestDanglingLinks:

    def rewrite(self, text, type_index, pages=PDF_PAGES, **kw):
        return link_fixer.rewrite_internal_links(
            text, "pdf", "Aspose.PDF", existing_pages=pages, type_index=type_index, overview_slug="aspose.pdf",
            repair_extra=True, **kw)

    def test_existing_page_is_left_alone(self, type_index):
        t = "[X](/pdf/aspose.pdf.lowcode.compressoptions)"
        assert self.rewrite(t, type_index) == t

    def test_missing_core_type_goes_to_reference_aspose_com(self, type_index):
        out = self.rewrite("[Doc](/pdf/aspose.pdf.document)", type_index)
        assert out == "[Doc](https://reference.aspose.com/pdf/net/aspose.pdf/document/)"

    def test_nested_type_uses_outer_type_segment(self, type_index):
        out = self.rewrite("[F](/pdf/aspose.pdf.forms.form.flattensettings)", type_index)
        assert out == "[F](https://reference.aspose.com/pdf/net/aspose.pdf.forms/form.flattensettings/)"

    def test_overview_page_link_goes_to_the_family_root(self, type_index):
        """Aspose.Pdf.md is renamed to _index.md: a link to it must point at /pdf/, not at a missing page."""
        stats = {}
        assert self.rewrite("[NS](/pdf/aspose.pdf)", type_index, stats=stats) == "[NS](/pdf/)"
        assert stats == {"overview_to_root": 1}
        assert self.rewrite("[NS](Aspose.Pdf.md#Aspose_Pdf)", type_index) == "[NS](/pdf/)"

    def test_namespace_without_overview_slug_goes_to_the_reference_site(self, type_index):
        out = link_fixer.rewrite_internal_links("[NS](/pdf/aspose.pdf)", "pdf", "Aspose.PDF", existing_pages=PDF_PAGES,
                                                type_index=type_index, repair_extra=True)
        assert out == "[NS](https://reference.aspose.com/pdf/net/aspose.pdf/)"

    def test_anchor_is_dropped_on_external_links(self, type_index):
        out = self.rewrite("[m](Aspose.Pdf.Document.md\\#Aspose\\_Pdf\\_Document\\_Save)", type_index)
        assert out == "[m](https://reference.aspose.com/pdf/net/aspose.pdf/document/)"

    def test_unknown_slug_is_left_and_counted(self, type_index):
        stats = {}
        t = "[?](/pdf/aspose.pdf.nosuchtype)"
        assert self.rewrite(t, type_index, stats=stats) == t
        assert stats == {"dangling_unresolved": 1}

    def test_family_root_link_is_never_rewritten(self, type_index):
        t = "[home](/pdf/)"
        assert self.rewrite(t, type_index) == t

    def test_disabled_by_default(self, type_index):
        t = r"[Doc](/pdf/aspose.pdf.document) [L](https://learn.microsoft.com/dotnet/api/system.collections.generic.list\-1)"
        out = link_fixer.rewrite_internal_links(t, "pdf", "Aspose.PDF", existing_pages=PDF_PAGES, type_index=type_index,
                                                overview_slug="aspose.pdf")
        assert out == t  # none of the opt-in repairs run unless repair_extra is set

    def test_real_page_every_core_link_resolves(self, type_index):
        src = read("pdf_en", "Aspose.Pdf.LowCode.PdfAOptionsBase.md")
        stats = {}
        out = self.rewrite(src, type_index, stats=stats)
        assert stats.get("dangling_rewritten", 0) >= 8 and stats.get("dangling_unresolved", 0) == 0
        for t in targets(out):
            if t.startswith("/pdf/") and t != "/pdf/":
                assert t[len("/pdf/"):] in PDF_PAGES, t  # only links to pages that exist are left on the site
        assert any(t.startswith("https://reference.aspose.com/pdf/net/aspose.pdf/") for t in targets(out))
        assert mask(out) == mask(src)
        assert self.rewrite(out, type_index) == out


class TestEscapedAbsoluteUrls:

    def fix(self, text):
        stats = {}
        return link_fixer.rewrite_internal_links(text, "pdf", "Aspose.PDF", repair_extra=True, stats=stats), stats

    def test_escaped_hyphen_in_microsoft_learn_link(self):
        out, stats = self.fix(r"[List<T>](https://learn.microsoft.com/dotnet/api/system.collections.generic.list\-1)")
        assert out == "[List<T>](https://learn.microsoft.com/dotnet/api/system.collections.generic.list-1)"
        assert stats == {"external_unescaped": 1}

    def test_escaped_underscore_is_removed_too(self):
        out, _ = self.fix(r"[x](https://example.com/a\_b\-c)")
        assert out == "[x](https://example.com/a_b-c)"

    def test_targets_with_other_escapes_are_left_alone(self):
        t = r"[x](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals)"
        assert self.fix(t)[0] == t

    def test_clean_absolute_links_are_untouched(self):
        t = "[x](https://learn.microsoft.com/dotnet/api/system.object)"
        out, stats = self.fix(t)
        assert out == t and stats == {}

    def test_real_page_external_links_are_clean_after_repair(self):
        src = read("pdf_en", "Aspose.Pdf.LowCode.OrganizerBaseOptions.md")
        assert any("\\" in t for t in targets(src) if t.startswith("http"))
        out, stats = self.fix(src)
        assert stats.get("external_unescaped", 0) >= 1
        assert not any("\\" in t for t in targets(out) if t.startswith("http"))
        assert mask(out) == mask(src)


class TestTypeIndex:

    def test_nested_chain_and_namespace(self):
        idx = link_fixer.TypeIndex(["Aspose.Pdf.Forms.Form", "Aspose.Pdf.Forms.Form.FlattenSettings", "Aspose.Pdf.Document"])
        assert idx.external_path("aspose.pdf.forms.form") == "aspose.pdf.forms/form/"
        assert idx.external_path("aspose.pdf.forms.form.flattensettings") == "aspose.pdf.forms/form.flattensettings/"
        assert idx.external_path("aspose.pdf") == "aspose.pdf/"
        assert idx.external_path("aspose.pdf.forms") == "aspose.pdf.forms/"
        assert idx.external_path("aspose.pdf.nothing") is None

    def test_generic_arity_marker_becomes_hyphen(self):
        idx = link_fixer.TypeIndex(["Aspose.Pdf.Things.Box`1"])
        assert idx.external_path("aspose.pdf.things.box-1") == "aspose.pdf.things/box-1/"

    def test_namespace_doc_entries_are_ignored(self):
        idx = link_fixer.TypeIndex(["Aspose.Pdf.NamespaceDoc", "Aspose.Pdf.Document"])
        assert idx.external_path("aspose.pdf.namespacedoc") is None

    def test_parse_from_xml_text(self):
        idx = link_fixer.TypeIndex.from_xml_text('<doc><members><member name="T:A.B.C"></member><member name="M:A.B.C.M"></member></members></doc>')
        assert idx.external_path("a.b.c") == "a.b/c/"


# ---------------------------------------------------------------------------
# repair_links.py (used for the existing pages)
# ---------------------------------------------------------------------------

class TestRepairTool:

    def make_root(self, tmp_path):
        root = tmp_path / "pdf"
        for lang, sub in (("en", "pdf_en"), ("de", "pdf_de")):
            d = root / lang
            d.mkdir(parents=True)
            for f in os.listdir(os.path.join(FIX, sub)):
                shutil.copy(os.path.join(FIX, sub, f), d / f)
        # the German folder needs the target page too
        shutil.copy(os.path.join(FIX, "pdf_en", "Aspose.Pdf.LowCode.OrganizerBaseOptions.md"), root / "de")
        return root

    def run(self, root, apply_changes):
        return repair_links.run(str(root), "pdf", "Aspose.PDF", os.path.join(FIX, "types.xml"), True, apply_changes)

    def test_dry_run_writes_nothing(self, tmp_path):
        root = self.make_root(tmp_path)
        before = {p: p.read_bytes() for p in root.rglob("*.md")}
        rep = self.run(root, apply_changes=False)
        assert rep["problems"] == []
        assert rep["totals"]["anchored_rewritten"] > 0
        assert {p: p.read_bytes() for p in root.rglob("*.md")} == before

    def test_apply_repairs_english_and_locale_then_is_idempotent(self, tmp_path):
        root = self.make_root(tmp_path)
        rep = self.run(root, apply_changes=True)
        assert rep["problems"] == []
        assert rep["totals"]["anchored_bad"] == 0 and rep["totals"]["anchored_checked"] > 0
        for p in root.rglob("*.md"):
            for t in targets(p.read_text(encoding="utf-8")):
                assert ".md" not in t and "\\" not in t, (p.name, t)
        again = self.run(root, apply_changes=False)
        assert again["totals"]["files_changed"] == 0

    def test_broken_anchor_is_reported(self, tmp_path):
        root = self.make_root(tmp_path)
        target = root / "en" / "Aspose.Pdf.LowCode.OrganizerBaseOptions.md"
        target.write_text(re.sub(r'<a id="[^"]*Inputs"></a>', "", target.read_text(encoding="utf-8")), encoding="utf-8")
        rep = self.run(root, apply_changes=False)
        assert any("not found" in p for p in rep["problems"])

    def test_crlf_files_keep_their_line_endings(self, tmp_path):
        root = self.make_root(tmp_path)
        p = root / "en" / "Aspose.Pdf.LowCode.CompressOptions.md"
        p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.run(root, apply_changes=True)
        data = p.read_bytes()
        assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b"")


# ---------------------------------------------------------------------------
# postprocessor.py end to end (runs the real script in a temp workspace)
# ---------------------------------------------------------------------------

RAW_COMPRESS = """# <a id="Aspose_Pdf_LowCode_CompressOptions"></a> Class CompressOptions

Namespace: [Aspose.Pdf.LowCode](Aspose.Pdf.LowCode.md)
Assembly: Aspose.PDF.dll

Represents Compress options.

```csharp
public sealed class CompressOptions : OrganizerBaseOptions
```

#### Inheritance

[OrganizerBaseOptions](Aspose.Pdf.LowCode.OrganizerBaseOptions.md) ←
[CompressOptions](Aspose.Pdf.LowCode.CompressOptions.md)

#### Inherited Members

[OrganizerBaseOptions.Inputs](Aspose.Pdf.LowCode.OrganizerBaseOptions.md\\#Aspose\\_Pdf\\_LowCode\\_OrganizerBaseOptions\\_Inputs),
[Document.Save\\(string\\)](Aspose.Pdf.Document.md\\#Aspose\\_Pdf\\_Document\\_Save\\_System\\_String\\_)
"""

RAW_BASE = """# <a id="Aspose_Pdf_LowCode_OrganizerBaseOptions"></a> Class OrganizerBaseOptions

Namespace: [Aspose.Pdf.LowCode](Aspose.Pdf.LowCode.md)
Assembly: Aspose.PDF.dll

Base options.

```csharp
public abstract class OrganizerBaseOptions
```

### <a id="Aspose_Pdf_LowCode_OrganizerBaseOptions_Inputs"></a> Inputs
"""

RAW_NS = """# <a id="Aspose_Pdf_LowCode"></a> Namespace Aspose.Pdf.LowCode

Namespace: [Aspose.Pdf](Aspose.Pdf.md)
Assembly: Aspose.PDF.dll

Low code.
"""


class TestPostprocessorEndToEnd:

    def run_postprocessor(self, tmp_path, env_extra=None):
        pytest.importorskip("bs4")
        api = tmp_path / "workspace" / "docfx" / "api"
        api.mkdir(parents=True)
        (api / "Aspose.Pdf.LowCode.CompressOptions.md").write_text(RAW_COMPRESS, encoding="utf-8")
        (api / "Aspose.Pdf.LowCode.OrganizerBaseOptions.md").write_text(RAW_BASE, encoding="utf-8")
        (api / "Aspose.Pdf.LowCode.md").write_text(RAW_NS, encoding="utf-8")
        (api / "Aspose.Pdf.md").write_text(RAW_NS.replace("Aspose.Pdf.LowCode", "Aspose.Pdf"), encoding="utf-8")
        shutil.copy(os.path.join(FIX, "types.xml"), tmp_path / "workspace" / "docfx" / "Aspose.PDF.xml")
        env = dict(os.environ)
        env.pop("REFERENCE_LINK_REPAIR_FAMILIES", None)
        env.update(env_extra or {})
        r = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "postprocessor.py"), "Aspose.PDF", "26.10.0"],
            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        return api

    def test_anchored_links_and_dangling_core_links(self, tmp_path):
        api = self.run_postprocessor(tmp_path)
        out = (api / "Aspose.Pdf.LowCode.CompressOptions.md").read_text(encoding="utf-8")
        assert "[OrganizerBaseOptions.Inputs](/pdf/aspose.pdf.lowcode.organizerbaseoptions/#Aspose_Pdf_LowCode_OrganizerBaseOptions_Inputs)" in out
        # plain links keep their historic form (no trailing slash)
        assert "[OrganizerBaseOptions](/pdf/aspose.pdf.lowcode.organizerbaseoptions)" in out
        # core type that is not generated -> reference.aspose.com
        assert "[Document.Save\\(string\\)](https://reference.aspose.com/pdf/net/aspose.pdf/document/)" in out
        # the namespace link of the namespace page points at the family root, and the overview is _index.md
        ns = (api / "Aspose.Pdf.LowCode.md").read_text(encoding="utf-8")
        assert "Namespace: [Aspose.Pdf](/pdf/)" in ns
        assert (api / "_index.md").exists()
        assert ".md" not in "".join(targets(out)) and "\\" not in "".join(targets(out))

    def test_extra_repairs_can_be_disabled_per_family(self, tmp_path):
        api = self.run_postprocessor(tmp_path, {"REFERENCE_LINK_REPAIR_FAMILIES": "words"})
        out = (api / "Aspose.Pdf.LowCode.CompressOptions.md").read_text(encoding="utf-8")
        assert "(/pdf/aspose.pdf.document/#Aspose_Pdf_Document_Save_System_String_)" in out  # anchored fix still applies
        assert "reference.aspose.com" not in out
