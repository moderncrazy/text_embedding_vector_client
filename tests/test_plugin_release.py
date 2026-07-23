import unittest
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def author_values(content):
    return [
        value.strip()
        for value in re.findall(r"(?m)^[ \t]*author:[ \t]*([^\r\n]*)$", content)
    ]


def top_level_author_values(content):
    return [
        value.strip()
        for value in re.findall(r"(?m)^author:[ \t]*([^\r\n]*)$", content)
    ]


def identity_author_values(content):
    identity_block = re.search(
        r"(?m)^identity:\r?\n((?:^(?:  |\t).*(?:\r?\n|$))*)",
        content,
    )
    if identity_block is None:
        return []

    return [
        value.strip()
        for value in re.findall(
            r"(?m)^  author:[ \t]*([^\r\n]*)$", identity_block.group(1)
        )
    ]


class PluginReleaseIdentityTests(unittest.TestCase):
    def test_manifest_release_and_schema_versions(self):
        manifest = (ROOT / "manifest.yaml").read_text(encoding="utf-8")

        self.assertRegex(manifest, r"(?m)^version: 0\.0\.4$")
        self.assertRegex(manifest, r"(?m)^  version: 0\.0\.1$")

    def test_all_plugin_identity_authors_are_moderncrazy(self):
        manifest = (ROOT / "manifest.yaml").read_text(encoding="utf-8")
        self.assertEqual(author_values(manifest), ["moderncrazy"])
        self.assertEqual(top_level_author_values(manifest), ["moderncrazy"])

        identity_files = [
            ROOT / "provider/embedding-client.yaml",
            ROOT / "tools/embedding-client.yaml",
        ]
        for path in identity_files:
            with self.subTest(path=path.relative_to(ROOT)):
                content = path.read_text(encoding="utf-8")
                self.assertEqual(author_values(content), ["moderncrazy"])
                self.assertEqual(identity_author_values(content), ["moderncrazy"])
                self.assertNotIn("siyu", content.lower())

    def test_author_location_rejects_moved_identity_author(self):
        identity_files = [
            ROOT / "provider/embedding-client.yaml",
            ROOT / "tools/embedding-client.yaml",
        ]

        for path in identity_files:
            with self.subTest(path=path.relative_to(ROOT)):
                moved_author = path.read_text(encoding="utf-8").replace(
                    "  author: moderncrazy",
                    "author: moderncrazy",
                    1,
                )
                self.assertEqual(identity_author_values(moved_author), [])

    def test_release_identity_files_are_lf_normalized(self):
        normalized_files = [
            ROOT / "manifest.yaml",
            ROOT / "provider/embedding-client.yaml",
            ROOT / "tools/embedding-client.yaml",
            ROOT / ".difyignore",
        ]

        for path in normalized_files:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn(b"\r", path.read_bytes())

    def test_source_manifest_awk_derives_byte_exact_package_name(self):
        package_name = subprocess.check_output(
            [
                "sh",
                "-c",
                'PLUGIN_NAME="$(awk \'$1 == "name:" && $0 !~ /^[[:space:]]/ { print $2; exit }\' manifest.yaml)"; '
                'VERSION="$(awk \'$1 == "version:" && $0 !~ /^[[:space:]]/ { print $2; exit }\' manifest.yaml)"; '
                'printf "%s" "${PLUGIN_NAME}-${VERSION}.difypkg"',
            ],
            cwd=ROOT,
        )

        self.assertEqual(package_name, b"text_embedding_vector_client-0.0.4.difypkg")

    def test_crlf_manifest_awk_derives_byte_exact_package_name(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture = Path(temporary_directory) / "manifest.yaml"
            fixture.write_bytes(
                b"version: 0.0.4\r\n"
                b"author: moderncrazy\r\n"
                b"name: text_embedding_vector_client\r\n"
            )
            package_name = subprocess.check_output(
                [
                    "sh",
                    "-c",
                    'PLUGIN_NAME="$(awk \'$1 == "name:" && $0 !~ /^[[:space:]]/ { sub(/\\r$/, ""); print $2; exit }\' "$1")"; '
                    'VERSION="$(awk \'$1 == "version:" && $0 !~ /^[[:space:]]/ { sub(/\\r$/, ""); print $2; exit }\' "$1")"; '
                    'printf "%s" "${PLUGIN_NAME}-${VERSION}.difypkg"',
                    "sh",
                    str(fixture),
                ]
            )

        self.assertEqual(package_name, b"text_embedding_vector_client-0.0.4.difypkg")

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
        self.assertIn('$1 == "author:" && $0 !~ /^[[:space:]]/', workflow)
        self.assertGreaterEqual(workflow.count("sub(/\\r$/, \"\")"), 6)
        self.assertIn('[ "$AUTHOR" != "moderncrazy" ]', workflow)
        self.assertIn('echo "author=$AUTHOR" >> "$GITHUB_OUTPUT"', workflow)

    def test_workflow_checks_package_safety_before_release_creation(self):
        workflow = self.workflow()

        self.assertIn('unzip -Z1 "$PACKAGE_NAME" > "$ARCHIVE_LIST"', workflow)
        self.assertIn('unzip -t "$PACKAGE_NAME"', workflow)
        self.assertIn('unzip -p "$PACKAGE_NAME" manifest.yaml > "$PACKAGED_MANIFEST"', workflow)
        self.assertIn("grep -Eq", workflow)
        self.assertIn("git metadata", workflow.lower())
        self.assertIn('PACKAGE_NAME: ${{ steps.manifest.outputs.package_name }}', workflow)
        self.assertIn('PLUGIN_NAME: ${{ steps.manifest.outputs.plugin_name }}', workflow)
        self.assertIn('VERSION: ${{ steps.manifest.outputs.version }}', workflow)
        self.assertIn('AUTHOR: ${{ steps.manifest.outputs.author }}', workflow)
        self.assertIn('[ "$PACKAGED_PLUGIN_NAME" != "$PLUGIN_NAME" ]', workflow)
        self.assertIn('[ "$PACKAGED_VERSION" != "$VERSION" ]', workflow)
        self.assertIn('[ "$PACKAGED_AUTHOR" != "$AUTHOR" ]', workflow)
        package = workflow.index('"$RUNNER_TEMP/bin/dify-plugin" plugin package')
        integrity = workflow.index('unzip -t "$PACKAGE_NAME"')
        archive_listing = workflow.index('unzip -Z1 "$PACKAGE_NAME"')
        git_rejection = workflow.index("Package contains Git metadata")
        packaged_manifest = workflow.index('unzip -p "$PACKAGE_NAME" manifest.yaml')
        comparison = workflow.index("Packaged manifest does not match")
        release_lookup = workflow.index("curl --silent --show-error --write-out")
        release_creation = workflow.index("gh release create")
        self.assertLess(package, integrity)
        self.assertLess(integrity, archive_listing)
        self.assertLess(archive_listing, git_rejection)
        self.assertLess(git_rejection, packaged_manifest)
        self.assertLess(packaged_manifest, comparison)
        self.assertLess(comparison, release_lookup)
        self.assertLess(release_lookup, release_creation)
        self.assertIn("--verify-tag", workflow)

    def test_workflow_release_lookup_fails_closed(self):
        workflow = self.workflow()

        self.assertIn("API_URL: ${{ github.api_url }}", workflow)
        self.assertIn("REPOSITORY: ${{ github.repository }}", workflow)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", workflow)
        self.assertIn('"$API_URL/repos/$REPOSITORY/releases/tags/$RELEASE_TAG"', workflow)
        self.assertIn('HTTP_STATUS="$(curl --silent --show-error --write-out \'%{http_code}\' --output /dev/null', workflow)
        self.assertIn('case "$HTTP_STATUS" in', workflow)
        self.assertIn('200)', workflow)
        self.assertIn('404)', workflow)
        self.assertIn('*)', workflow)
        self.assertNotIn("gh release view", workflow)

    def test_workflow_creates_expected_release(self):
        workflow = self.workflow()

        self.assertIn("GH_TOKEN: ${{ github.token }}", workflow)
        self.assertIn("--generate-notes", workflow)
        self.assertIn('--title "Text Embedding Vector Client $RELEASE_TAG"', workflow)


if __name__ == "__main__":
    unittest.main()
