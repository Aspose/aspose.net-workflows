"""Tests for scripts/deploy/detect_changes.py (WS7b: www.aspose.net is never deployed)."""

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "detect_changes",
    Path(__file__).resolve().parents[1] / "scripts" / "deploy" / "detect_changes.py",
)
dc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(dc)

WWW = "www.aspose.net.yml"


class WwwNeverDeployedTests(unittest.TestCase):
    def test_excluded_constant(self):
        self.assertIn(WWW, dc.EXCLUDED_WORKFLOWS)

    def test_all_workflows_excludes_www_keeps_others(self):
        wfs = dc.get_all_deploy_workflows()
        self.assertNotIn(WWW, wfs)
        for keep in ("websites.aspose.net.yml", "blog.aspose.net.yml", "about.aspose.net.yml"):
            self.assertIn(keep, wfs)

    def test_global_paths_exclude_www(self):
        for path in ("themes/x/layout.html", "layouts/a.html", "static/a.css", "i18n/en.toml"):
            wfs, is_global = dc.map_path_to_workflow(path)
            self.assertTrue(is_global, path)
            self.assertNotIn(WWW, wfs, path)
            self.assertIn("websites.aspose.net.yml", wfs, path)

    def test_www_content_and_config_map_to_nothing(self):
        for path in ("content/www.aspose.net/index.md", "configs/www.aspose.net.toml"):
            wfs, is_global = dc.map_path_to_workflow(path)
            self.assertFalse(is_global, path)
            self.assertEqual(wfs, set(), path)

    def test_other_whole_sections_still_map(self):
        wfs, _ = dc.map_path_to_workflow("content/websites.aspose.net/index.md")
        self.assertEqual(wfs, {"websites.aspose.net.yml"})

    def test_drop_excluded(self):
        self.assertEqual(dc.drop_excluded({WWW, "blog.aspose.net.yml"}), {"blog.aspose.net.yml"})


if __name__ == "__main__":
    unittest.main()
