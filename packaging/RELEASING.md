# Preparing a GPLv3 release

1. Keep `APP_VERSION`, `pyproject.toml` and the Inno Setup version aligned. Record the exact dependency versions in `requirements-release.txt` and `license_sources.toml`; update source URLs/checksums and native license notices when changing dependencies or platforms.
2. Build with `scripts/build_windows.bat` or `scripts/build_macos.sh`. These scripts prepare the license bundle and source archives. A missing or mismatched source/license must fail preparation rather than silently producing a release with missing notices.
3. Review the generated `SOURCE_MANIFEST.toml`, `THIRD_PARTY_NOTICES.md`, native library inventory and source archives. Confirm the binary libraries originate from the reviewed distributions, and include any vendor or local patches needed to reproduce them.
4. Run the tests and inspect the application: **About** must state GPLv3, no warranty and redistribution rights; **Licenses and source code** must open the installed legal documents. Verify the installer copies those documents and Qt libraries remain replaceable.
5. Upload the binary artifact, matching application source ZIP, dependency source ZIP and SHA-256 file from `dist/release/` to the same release. Paste the generated release notes next to the binary download links. Keep these sources available and regenerate the checksums when adding or changing a binary asset.

No script in this project publishes to GitHub. The maintainer must upload the reviewed artifacts; local file preparation does not satisfy source access for an already public binary.

## Releases 1.0.3 and 1.0.4

Changing the current `LICENSE` does not repair a previously published installer. For each previous binary:

- Extract and inventory its actual contents without assuming they match the current virtual environment.
- Recover the exact source revision, dependency versions, sources, patches and build scripts used for that binary.
- Prepare its complete notices and corresponding-source access. Retain the original MIT permissions on application code previously licensed under MIT while making the combined application's GPL terms explicit.
- Rebuild an installer with the corrected legal documents, verify it, and update the release assets and description. Avoid reusing the same filename silently; explain what changed and provide new checksums.
- If a compliant replacement cannot yet be provided, consider withdrawing that installer from download until the missing materials are recovered.

The original historical MIT notice remains in `licenses/APIRestDesk-MIT-prior.txt`. Do not erase third-party copyright notices or claim that changing the repository license retroactively revokes grants already made.

## Before claiming full compliance

Verify original authorship/provenance of legacy code and screenshot contents, wheel build provenance and patches, Microsoft runtime redistribution terms and native components not identifiable from the Python dependency metadata. Repeat the native and installer checks on macOS/Linux when distributing those platforms. Preserve the audit's remaining limitations rather than presenting a generated license inventory as legal certification.
