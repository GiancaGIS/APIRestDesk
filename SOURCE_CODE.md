# Source code, rebuilding and library replacement

APIRestDesk is Copyright (c) 2026 GiancaGIS and distributed under GNU GPL version 3 only. The full license is in `LICENSE`. It comes without warranty. Dependency licenses and notices are retained in `licenses/` and `THIRD_PARTY_NOTICES.md`.

## Obtaining the source of a binary release

Open the release page for the exact version shown in **About**, at:

https://github.com/GiancaGIS/APIRestDesk/releases

For every newly prepared binary release, the distributor must publish these files beside the installer or application download, without an additional charge:

- `APIRestDesk-<version>-source.zip`: the matching application source, assets, legal documents, dependency constraints and build scripts.
- `APIRestDesk-<version>-dependency-sources.zip`: the exact upstream source archives recorded in `SOURCE_MANIFEST.toml`, together with the manifest and source instructions.
- `APIRestDesk-<version>-SHA256SUMS.txt`: checksums of the release artifacts.

The built-in GitHub source ZIP alone does not contain the dependency sources. Source archives prepared locally are not available to recipients until the distributor uploads them. If these assets are missing, the release's distribution preparation is incomplete; the maintainer must provide the missing corresponding sources. Existing MIT-era releases require separate review and correction.

`SOURCE_MANIFEST.toml` also gives version-specific HTTPS source URLs and SHA-256 checksums. Source archives are retained alongside the release so that recipients do not depend only on a changing upstream download site. The distributor remains responsible for making the required sources available under the applicable licenses.

## Rebuilding the application

Extract the matching application source ZIP. Use the Python version recorded under `CPython` in its manifest for the reviewed build, create a virtual environment, and install its release constraints:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-release.txt
.venv\Scripts\python.exe -m pip install --no-build-isolation -e ".[packaging]"
```

On macOS/Linux use `.venv/bin/python` instead. The application supports Python >=3.11; release inventories must be regenerated when changing the interpreter, platform or dependency versions.

Extract the dependency ZIP, and copy its source archives into `build/license-sources/`. This directory is only an archive cache; do not execute third-party code from it merely to inspect licenses. Then run:

```powershell
.venv\Scripts\python.exe scripts/prepare_licenses.py
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean packaging/pyinstaller/APIRestDesk.spec
.venv\Scripts\python.exe scripts/prepare_release_sources.py
```

Alternatively, `scripts/build_windows.bat` and `scripts/build_macos.sh` install the constraints, obtain any missing sources, prepare the license bundle and build release artifacts. A Windows installer additionally requires Inno Setup 6. `--skip-installer` creates the Windows application folder and source artifacts without an installer.

After manually compiling the matching Windows installer, run `scripts/prepare_release_sources.py --include-installer` to include it in the release and checksums. An older installer is rejected; it must be compiled after the current binary/legal bundle.

## Rebuilding dependencies and replacing Qt

The dependency ZIP contains source archives, not merely binary wheels. PyQt6's source includes its SIP interface definitions and build configuration. The Qt archives include their source, build scripts, upstream license texts and embedded third-party code. See their included build instructions and [Qt build documentation](https://doc.qt.io/qt-6/build-sources.html); PyQt's supported build tools and prerequisites are declared in its source `pyproject.toml`. Keep any downstream patches with the corresponding release sources when using modified dependencies.

To use locally rebuilt libraries in a new application build, install those libraries/bindings in the virtual environment before running PyInstaller. Update the reviewed profile, source archives and notices to match modifications; do not silently bypass the version checks for a published release.

Windows bundles use separate Qt DLLs under `_internal/PyQt6/Qt6/bin` and plugins under `_internal/PyQt6/Qt6/plugins`; they are not linked into the application executable. Replace the relevant DLLs and dependent plugins with an ABI-compatible Qt build matching the PyQt binding and architecture. Keep the original files as a backup and run the application to verify compatibility. macOS bundles contain Qt frameworks/libraries inside the `.app`; replacing them may require re-signing the modified bundle locally. Rebuilding the application against the modified libraries is also supported by the supplied source and spec.

APIRestDesk imposes no contractual prohibition on reverse engineering needed to debug modifications to LGPL-covered libraries. The project adds no lock that deliberately prevents library replacement. This permission does not alter the separate terms of system components such as Microsoft runtime libraries.

## Scope of this preparation

The current inventory covers the reviewed Python packages, Qt Base/SVG/Image Formats, Python distribution notices, OpenSSL and the available Inno Setup license. Windows also includes source/license materials for zstd, zlib-ng, libffi and xz, using the reviewed CPython native profile. Qt PDF and the optional software OpenGL fallback are excluded because the application does not use them. Native runtime provenance, upstream wheel patches, additional statically incorporated components and new platforms still require review; these documents are not a blanket legal certification.
