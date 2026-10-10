# Third-party notices

APIRestDesk is Copyright (c) 2026 GiancaGIS, licensed under GPL-3.0-only.
Dependency copyrights and license terms remain with their respective authors.
The original upstream texts and attribution records are provided in `licenses/`.

PyQt6: Copyright (c) 2026 Riverbank Computing Limited; GNU GPL version 3 only.
Qt: Copyright The Qt Company Ltd. and other contributors; distributed using the applicable LGPLv3 permissions. See the module licenses and embedded third-party notices.
Qt and Python trademarks belong to their respective owners; no endorsement is implied.

| Component | Reviewed version | License / notices |
| --- | --- | --- |
| PyQt6 | 6.11.0 | GPL-3.0-only — `licenses/PyQt6/` |
| PyQt6-sip | 13.11.1 | BSD-2-Clause — `licenses/PyQt6-sip/` |
| httpx | 0.28.1 | BSD-3-Clause — `licenses/httpx/` |
| httpcore | 1.0.9 | BSD-3-Clause — `licenses/httpcore/` |
| anyio | 4.14.2 | MIT — `licenses/anyio/` |
| h11 | 0.16.0 | MIT — `licenses/h11/` |
| idna | 3.18 | BSD-3-Clause — `licenses/idna/` |
| certifi | 2026.6.17 | MPL-2.0 — `licenses/certifi/` |
| pyinstaller | 6.21.0 | GPLv2-or-later with a special exception which allows to use PyInstaller to build and distribute non-free programs (including commercial ones) — `licenses/pyinstaller/` |
| qtbase | 6.11.1 | See Qt and third-party license files — `licenses/qtbase/` |
| qtsvg | 6.11.1 | See Qt and third-party license files — `licenses/qtsvg/` |
| qtimageformats | 6.11.1 | See Qt and third-party license files — `licenses/qtimageformats/` |
| CPython | 3.14.5 | PSF-2.0 and incorporated software licenses — `licenses/CPython/` |
| OpenSSL | 3.0.20 | Apache-2.0 — `licenses/OpenSSL/` |
| zstd | 1.5.7 | BSD-3-Clause OR GPL-2.0-only; use the BSD option for the library — `licenses/zstd/` |
| zlib-ng | 2.2.4 | Zlib and incorporated software notices — `licenses/zlib-ng/` |
| xz | 5.2.5 | Public-domain liblzma and component-specific licenses; see COPYING — `licenses/xz/` |
| libffi | 3.4.4 | MIT — `licenses/libffi/` |
| PyQt6-Qt6 wheel | 6.11.1 | LGPLv3 — `licenses/PyQt6-Qt6/`; source is provided by the Qt module archives above |

Qt notices include upstream third-party license texts and attribution records for Qt Base, SVG, and Image Formats. See each `UPSTREAM_FILES.txt` for their original paths.
Qt PDF and the software OpenGL fallback are excluded from the application bundle because APIRestDesk does not use them.
PyInstaller's exception permits generated bundles under other licenses when dependency terms are met; it does not remove PyQt/Qt obligations.
Certifi's CA bundle retains MPL-2.0 notices; MPL applies to the covered files.
On Windows, Microsoft runtime components retain Microsoft's terms, separately from the GPL application; see the Python distribution notice in `licenses/CPython/WINDOWS_DISTRIBUTION_LICENSE.txt`.
The compiler and libraries used by Inno Setup retain their own notices. Where available, the installed Inno Setup license is included in `licenses/InnoSetup/`.
The previous APIRestDesk MIT notice concerns previously licensed copies, not the current overall application's license.

Source locations and SHA-256 values are recorded in `SOURCE_MANIFEST.toml`. For obtaining, rebuilding and modifying the release, see `SOURCE_CODE.md`.
These files document the reviewed build; a new dependency, native module, runtime or platform requires an updated inventory.
