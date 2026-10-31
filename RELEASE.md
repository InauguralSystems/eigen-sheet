# Release process

1. Review commits since the preceding tag and add one user-facing Markdown
   fragment per change under `changes/{added,breaking,changed,fixed,internal}`.
   Fragments are short bullet items and include their issue number.
2. Run `python3 tools/release.py X.Y.Z`. This updates `eigs.json`, the
   `sheet.eigs` `VERSION`, and the README package tag together; it assembles
   the fragments into `CHANGELOG.md` and archives the consumed inputs below
   `changes/archive/vX.Y.Z/`.
3. Add any broad summary needed to cover older commits that predate the
   fragment convention, then run `python3 tools/check_release_versions.py
   --self-test` and the full test entry point (`bash tests/test_smoke.sh` plus
   every CI oracle listed in `.github/workflows/test.yml`). Commit and merge.
4. Create and push the signed `vX.Y.Z` tag from the merged commit. For v0.2.0,
   DevBox performs this final step after issue #77 merges.

Do not publish a tag if the version check or tests fail.
