import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginReleaseIdentityTests(unittest.TestCase):
    def test_manifest_release_and_schema_versions(self):
        manifest = (ROOT / "manifest.yaml").read_text(encoding="utf-8")

        self.assertRegex(manifest, r"(?m)^version: 0\.0\.4$")
        self.assertRegex(manifest, r"(?m)^  version: 0\.0\.1$")

    def test_all_plugin_identity_authors_are_moderncrazy(self):
        identity_files = [
            ROOT / "manifest.yaml",
            ROOT / "provider/embedding-client.yaml",
            ROOT / "tools/embedding-client.yaml",
        ]

        for path in identity_files:
            with self.subTest(path=path.relative_to(ROOT)):
                content = path.read_text(encoding="utf-8")
                self.assertRegex(content, r"(?m)^\s*author: moderncrazy$")
                self.assertNotIn("siyu", content.lower())

    def test_package_excludes_git_metadata_in_directories_and_worktrees(self):
        ignored_entries = {
            line.strip()
            for line in (ROOT / ".difyignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertIn(".git", ignored_entries)
        self.assertIn(".git/", ignored_entries)


class PluginReleaseWorkflowTests(unittest.TestCase):
    def workflow(self):
        path = ROOT / ".github/workflows/plugin-release.yml"
        self.assertTrue(path.is_file(), "plugin release workflow must exist")
        return path.read_text(encoding="utf-8")

    def test_workflow_has_release_triggers_and_permission(self):
        workflow = self.workflow()

        self.assertIn('      - "v*"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("contents: write", workflow)

    def test_workflow_uses_pinned_official_cli_and_versioned_package(self):
        workflow = self.workflow()

        self.assertIn(
            "dify-plugin-daemon/releases/download/0.0.6/dify-plugin-linux-amd64",
            workflow,
        )
        self.assertIn(
            "2a79897a1284e1fa870f4d859595ee8a4b786d39917ae66f1e34d1021a96c87a",
            workflow,
        )
        self.assertIn("sha256sum -c", workflow)
        self.assertIn('plugin package . -o "$PACKAGE_NAME"', workflow)
        self.assertIn("package_name=${PLUGIN_NAME}-${VERSION}.difypkg", workflow)
        self.assertIn('EXPECTED_TAG="v${VERSION}"', workflow)
        self.assertIn('$1 == "name:" && $0 !~ /^[[:space:]]/', workflow)

    def test_workflow_rejects_invalid_or_existing_release(self):
        workflow = self.workflow()

        self.assertIn('unzip -Z1 "$PACKAGE_NAME" > "$ARCHIVE_LIST"', workflow)
        self.assertIn("grep -Eq", workflow)
        self.assertIn("git metadata", workflow.lower())
        self.assertLess(workflow.index("gh release view"), workflow.index("gh release create"))
        self.assertIn("--verify-tag", workflow)

    def test_workflow_creates_expected_release(self):
        workflow = self.workflow()

        self.assertIn("GH_TOKEN: ${{ github.token }}", workflow)
        self.assertIn("--generate-notes", workflow)
        self.assertIn('--title "Text Embedding Vector Client $RELEASE_TAG"', workflow)


if __name__ == "__main__":
    unittest.main()
