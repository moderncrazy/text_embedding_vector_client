# GitHub Dify Package Release

## Goal

Release version `0.0.4` of `text_embedding_vector_client` under the GitHub identity `moderncrazy`, with a verified `.difypkg` asset attached to GitHub Release `v0.0.4`.

## Identity and Version

Update the plugin release version in `manifest.yaml` from `0.0.3` to `0.0.4`. Keep the manifest schema version under `meta.version` unchanged at `0.0.1`.

Set every plugin identity author to `moderncrazy`:

- `manifest.yaml`
- `provider/embedding-client.yaml`
- `tools/embedding-client.yaml`

No labels, plugin names, provider names, tool names, or runtime behavior will change.

## Packaging Safety

Add `.git` to `.difyignore` so packaging from a normal checkout or linked worktree cannot include Git metadata. The release workflow will independently inspect the finished archive and fail if any `.git` path is present.

The expected asset name is:

`text_embedding_vector_client-0.0.4.difypkg`

## GitHub Release Workflow

Add a tag-driven GitHub Actions workflow based on `moderncrazy/dify-pdf-process-plugin`.

The workflow will:

1. Run when a `v*` tag is pushed, and support manual dispatch for an existing tag.
2. Require the release tag to equal `v` plus the top-level manifest version.
3. Download Dify plugin CLI `0.0.6` for Linux AMD64.
4. Verify the CLI against the pinned SHA-256 digest used by the reference repository.
5. Package the repository root with the official CLI.
6. Require a non-empty package and reject an archive containing Git metadata.
7. Refuse to overwrite an existing GitHub Release.
8. Create GitHub Release `v0.0.4`, titled `Text Embedding Vector Client v0.0.4`, with generated notes and the `.difypkg` asset.

The workflow uses the repository-scoped `github.token` with `contents: write`. No personal token is stored in source code, workflow files, logs, or release assets.

## Tests and Verification

Add standard-library unit tests that verify:

- the top-level release version is exactly `0.0.4` while `meta.version` remains `0.0.1`;
- all three identity YAML files use `author: moderncrazy` and no longer contain `siyu`;
- `.difyignore` excludes `.git`;
- the workflow has tag and manual triggers plus `contents: write`;
- the workflow uses the pinned official CLI URL and checksum;
- the tag/version check, versioned asset naming, archive inspection, non-overwrite check, and release title are present.

Run the existing embedding behavior tests together with the new release tests before committing. After pushing `main`, create and push annotated tag `v0.0.4`. Monitor the workflow and public Release until the asset is present.

## Failure Handling

Do not create or force-update the tag until the local tests and source checks pass. Do not overwrite an existing tag or Release. If GitHub Actions fails, preserve the tag and inspect the failed job before deciding whether a corrective commit and new version are required. Do not publish to the Dify Marketplace as part of this release.
