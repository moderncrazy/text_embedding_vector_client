# GitHub Dify Package Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish `text_embedding_vector_client` version `0.0.4` under author `moderncrazy` as a verified `.difypkg` asset on GitHub Release `v0.0.4`.

**Architecture:** Encode release identity and workflow requirements as standard-library tests. Use a tag-triggered GitHub Actions workflow, adapted from `moderncrazy/dify-pdf-process-plugin`, to download a pinned official Dify CLI, package the plugin, validate the archive, and create a non-overwriting GitHub Release.

**Tech Stack:** Python 3.12, `unittest`, GitHub Actions, Dify plugin CLI `0.0.6`, GitHub Releases

## Global Constraints

- The plugin release version must be exactly `0.0.4`; `meta.version` remains exactly `0.0.1`.
- Every plugin identity author must be exactly `moderncrazy`; no identity file may retain `siyu`.
- The release asset name must be exactly `text_embedding_vector_client-0.0.4.difypkg`.
- The release tag must be exactly `v0.0.4` and the Release title must be exactly `Text Embedding Vector Client v0.0.4`.
- The official Dify plugin CLI must be pinned to version `0.0.6` and SHA-256 `2a79897a1284e1fa870f4d859595ee8a4b786d39917ae66f1e34d1021a96c87a`.
- The package must exclude Git metadata, be non-empty, pass ZIP integrity validation, and contain `manifest.yaml` with version `0.0.4` and author `moderncrazy`.
- Do not change plugin names, labels, provider names, tool names, runtime behavior, dependencies, or Dify Marketplace state.
- Do not store or print a personal GitHub token; the release workflow uses `${{ github.token }}` with `contents: write`.
- Do not overwrite or force-update an existing tag or GitHub Release.

---

### Task 1: Update Release Identity

**Files:**
- Create: `tests/test_plugin_release.py`
- Modify: `manifest.yaml:1-3`
- Modify: `provider/embedding-client.yaml:1-3`
- Modify: `tools/embedding-client.yaml:1-4`
- Modify: `.difyignore`

**Interfaces:**
- Consumes: Dify plugin identity YAML files and packaging ignore rules
- Produces: release identity `moderncrazy/text_embedding_vector_client:0.0.4` and `.git` exclusion for normal repositories and linked worktrees

- [ ] **Step 1: Write failing identity and packaging-safety tests**

Create `tests/test_plugin_release.py`:

```python
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


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the identity tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_plugin_release.py -v
```

Expected: three failures showing top-level version `0.0.3`, author `siyu`, and missing exact `.git` ignore entry. Test import and discovery succeed.

- [ ] **Step 3: Apply the minimal identity changes**

In `manifest.yaml`, set:

```yaml
version: 0.0.4
type: plugin
author: moderncrazy
```

In `provider/embedding-client.yaml`, begin the identity block with:

```yaml
identity:
  author: moderncrazy
  name: "provider_embedding_client"
```

In `tools/embedding-client.yaml`, begin the identity block with:

```yaml
identity:
  name: text_2_vector
  author: moderncrazy
```

Keep `.git/` in `.difyignore` and add the exact linked-worktree entry beside it:

```text
.git
.git/
```

- [ ] **Step 4: Run the identity tests and full existing suite to verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Expected: nine tests pass: the six embedding behavior tests and three release identity tests.

- [ ] **Step 5: Verify the focused diff and commit**

Run:

```bash
python3 -c "import ast, pathlib; files = [pathlib.Path('tests/test_embedding_client.py'), pathlib.Path('tests/test_plugin_release.py')]; [ast.parse(file.read_text()) for file in files]; print('Parsed 2 test files successfully')"
git diff --check
git diff -- manifest.yaml provider/embedding-client.yaml tools/embedding-client.yaml .difyignore tests/test_plugin_release.py
```

Expected: both test files parse; whitespace check passes; the diff contains only the planned identity, version, ignore, and test changes.

Commit:

```bash
git add manifest.yaml provider/embedding-client.yaml tools/embedding-client.yaml .difyignore tests/test_plugin_release.py
git commit -m "chore: prepare plugin v0.0.4"
```

---

### Task 2: Add the Verified GitHub Release Workflow

**Files:**
- Create: `.github/workflows/plugin-release.yml`
- Modify: `tests/test_plugin_release.py`

**Interfaces:**
- Consumes: top-level `manifest.yaml` fields `name` and `version`, tag `v0.0.4`, repository-scoped `${{ github.token }}`
- Produces: GitHub Release asset `text_embedding_vector_client-0.0.4.difypkg` titled `Text Embedding Vector Client v0.0.4`

- [ ] **Step 1: Add failing workflow contract tests**

Add this class to `tests/test_plugin_release.py` before the `if __name__ == "__main__"` block:

```python
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


```

- [ ] **Step 2: Run the workflow tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests/test_plugin_release.py -v
```

Expected: the three identity tests pass and four workflow tests fail with `plugin release workflow must exist`.

- [ ] **Step 3: Add the tag-driven packaging and Release workflow**

Create `.github/workflows/plugin-release.yml`:

```yaml
name: Package and Release Plugin

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:
    inputs:
      tag:
        description: Existing release tag (for example, v0.0.4)
        required: true
        type: string

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Resolve release tag
        id: release
        env:
          EVENT_NAME: ${{ github.event_name }}
          REF_NAME: ${{ github.ref_name }}
          DISPATCH_TAG: ${{ inputs.tag }}
        run: |
          if [ "$EVENT_NAME" = "workflow_dispatch" ]; then
            RELEASE_TAG="$DISPATCH_TAG"
          else
            RELEASE_TAG="$REF_NAME"
          fi

          if [ -z "$RELEASE_TAG" ]; then
            echo "Release tag is required." >&2
            exit 1
          fi

          echo "tag=$RELEASE_TAG" >> "$GITHUB_OUTPUT"

      - name: Check out release tag
        uses: actions/checkout@v4
        with:
          ref: ${{ steps.release.outputs.tag }}

      - name: Read and validate manifest
        id: manifest
        env:
          RELEASE_TAG: ${{ steps.release.outputs.tag }}
        run: |
          PLUGIN_NAME="$(awk '$1 == "name:" && $0 !~ /^[[:space:]]/ { print $2; exit }' manifest.yaml)"
          VERSION="$(awk '$1 == "version:" && $0 !~ /^[[:space:]]/ { print $2; exit }' manifest.yaml)"
          EXPECTED_TAG="v${VERSION}"

          if [ -z "$PLUGIN_NAME" ] || [ -z "$VERSION" ]; then
            echo "Unable to read plugin name or version from manifest.yaml." >&2
            exit 1
          fi

          if [ "$RELEASE_TAG" != "$EXPECTED_TAG" ]; then
            echo "Release tag $RELEASE_TAG does not match manifest version $VERSION." >&2
            exit 1
          fi

          echo "plugin_name=$PLUGIN_NAME" >> "$GITHUB_OUTPUT"
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"
          echo "package_name=${PLUGIN_NAME}-${VERSION}.difypkg" >> "$GITHUB_OUTPUT"

      - name: Download Dify plugin CLI
        env:
          CLI_SHA256: 2a79897a1284e1fa870f4d859595ee8a4b786d39917ae66f1e34d1021a96c87a
        run: |
          mkdir -p "$RUNNER_TEMP/bin"
          curl -fL --retry 3 -o "$RUNNER_TEMP/bin/dify-plugin" "https://github.com/langgenius/dify-plugin-daemon/releases/download/0.0.6/dify-plugin-linux-amd64"
          echo "$CLI_SHA256  $RUNNER_TEMP/bin/dify-plugin" | sha256sum -c -
          chmod +x "$RUNNER_TEMP/bin/dify-plugin"

      - name: Package plugin
        env:
          PACKAGE_NAME: ${{ steps.manifest.outputs.package_name }}
        run: |
          "$RUNNER_TEMP/bin/dify-plugin" plugin package . -o "$PACKAGE_NAME"
          test -s "$PACKAGE_NAME"

          ARCHIVE_LIST="$RUNNER_TEMP/package-contents.txt"
          unzip -Z1 "$PACKAGE_NAME" > "$ARCHIVE_LIST"

          if grep -Eq '(^|/)\.git(/|$)' "$ARCHIVE_LIST"; then
            echo "Package contains Git metadata; refusing to publish it." >&2
            exit 1
          fi

      - name: Ensure release does not exist
        env:
          GH_TOKEN: ${{ github.token }}
          RELEASE_TAG: ${{ steps.release.outputs.tag }}
        run: |
          if gh release view "$RELEASE_TAG" >/dev/null 2>&1; then
            echo "Release $RELEASE_TAG already exists; refusing to overwrite it." >&2
            exit 1
          fi

      - name: Create GitHub Release
        env:
          GH_TOKEN: ${{ github.token }}
          PACKAGE_NAME: ${{ steps.manifest.outputs.package_name }}
          RELEASE_TAG: ${{ steps.release.outputs.tag }}
        run: |
          gh release create "$RELEASE_TAG" "$PACKAGE_NAME" --verify-tag --generate-notes --title "Text Embedding Vector Client $RELEASE_TAG"
```

- [ ] **Step 4: Run all tests and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

Expected: thirteen tests pass: six embedding tests, three identity tests, and four workflow tests.

- [ ] **Step 5: Run source checks and commit**

Run:

```bash
python3 -c "import ast, pathlib; files = list(pathlib.Path('tests').glob('test_*.py')); [ast.parse(file.read_text()) for file in files]; print(f'Parsed {len(files)} test files successfully')"
git diff --check
git diff -- .github/workflows/plugin-release.yml tests/test_plugin_release.py
```

Expected: all test files parse; whitespace check passes; the focused diff contains only the planned workflow and contract tests.

Commit:

```bash
git add .github/workflows/plugin-release.yml tests/test_plugin_release.py
git commit -m "ci: release packaged plugin from tags"
```

---

### Task 3: Publish and Verify GitHub Release v0.0.4

**Files:**
- External write: GitHub branch `main`
- External write: annotated Git tag `v0.0.4`
- External write: GitHub Release `v0.0.4`
- External artifact: `text_embedding_vector_client-0.0.4.difypkg`

**Interfaces:**
- Consumes: tested release commit on `main` and `.github/workflows/plugin-release.yml`
- Produces: remotely tracked `main`, immutable release tag `v0.0.4`, successful release workflow, downloadable and verified `.difypkg` asset

- [ ] **Step 1: Perform the pre-release gate**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git status --short --branch
git tag --list v0.0.4
git ls-remote --tags origin refs/tags/v0.0.4
```

Expected: thirteen tests pass; the working tree is clean; both local and remote tag checks return no tag. Stop rather than overwrite if either tag exists.

- [ ] **Step 2: Push the tested main branch**

Run:

```bash
git push origin main
```

Expected: `main` advances successfully without force-push.

- [ ] **Step 3: Create and push the release tag**

Run:

```bash
git tag -a v0.0.4 -m "Release v0.0.4"
git push origin v0.0.4
```

Expected: annotated tag `v0.0.4` is created once and pushed without force.

- [ ] **Step 4: Monitor the GitHub workflow to completion**

Use the public GitHub Actions API until the run for tag `v0.0.4` reaches `completed`:

```bash
curl -fsSL "https://api.github.com/repos/moderncrazy/text_embedding_vector_client/actions/runs?event=push&per_page=20" -o /private/tmp/text_embedding_vector_client-actions.json
python3 -c "import json; data=json.load(open('/private/tmp/text_embedding_vector_client-actions.json')); runs=[r for r in data['workflow_runs'] if r['head_branch']=='v0.0.4']; assert runs, 'v0.0.4 workflow run not found'; run=runs[0]; print(run['status'], run['conclusion'], run['html_url']); assert run['status']=='completed'; assert run['conclusion']=='success'"
```

Expected: the matching run is `completed success`. If it is still queued or running, wait briefly and repeat. If it fails, inspect the job before making any new tag or Release decision.

- [ ] **Step 5: Verify the public Release and download the asset**

Run:

```bash
curl -fsSL "https://api.github.com/repos/moderncrazy/text_embedding_vector_client/releases/tags/v0.0.4" -o /private/tmp/text_embedding_vector_client-release.json
python3 -c "import json; data=json.load(open('/private/tmp/text_embedding_vector_client-release.json')); assets={a['name']:a for a in data['assets']}; asset=assets['text_embedding_vector_client-0.0.4.difypkg']; assert asset['size'] > 0; print(data['html_url']); print(asset['browser_download_url']); print(asset['size'])"
curl -fL "https://github.com/moderncrazy/text_embedding_vector_client/releases/download/v0.0.4/text_embedding_vector_client-0.0.4.difypkg" -o /private/tmp/text_embedding_vector_client-0.0.4.difypkg
```

Expected: Release `v0.0.4` exists, contains exactly named non-empty asset, and the asset downloads successfully.

- [ ] **Step 6: Validate the published package contents**

Run:

```bash
unzip -t /private/tmp/text_embedding_vector_client-0.0.4.difypkg
unzip -Z1 /private/tmp/text_embedding_vector_client-0.0.4.difypkg
unzip -p /private/tmp/text_embedding_vector_client-0.0.4.difypkg manifest.yaml
```

Expected: ZIP integrity passes; no `.git` path appears; package includes the plugin sources and metadata; packaged `manifest.yaml` has top-level `version: 0.0.4` and `author: moderncrazy`.

- [ ] **Step 7: Verify final repository synchronization**

Run:

```bash
git fetch origin main --tags
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
git rev-parse 'v0.0.4^{}'
```

Expected: the working tree is clean; `HEAD`, `origin/main`, and peeled tag `v0.0.4^{}` are the same tested release commit.
