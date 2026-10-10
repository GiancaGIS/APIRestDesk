"""Prepare binary, application-source and dependency-source archives without publishing."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import stat
import sys
import tomllib
import zipfile

from prepare_licenses import CACHE, DOCUMENTS, ROOT, check, digest


SOURCE_DIRECTORIES = ("api_rest_desk", "scripts", "packaging", "tests", "images", "licenses")
SOURCE_SUFFIXES = {".py", ".md", ".txt", ".toml", ".spec", ".iss", ".bat", ".sh", ".png", ".svg", ".ico", ".icns"}
SOURCE_FILES = (*DOCUMENTS, "README.md", "LICENSE_AUDIT.md", "LICENSE_REMEDIATION.md", "pyproject.toml",
                "requirements.txt", "requirements-release.txt", "MANIFEST.in", ".gitignore",
                "launch_api_rest_desk.py", "run_windows.bat", "run_mac.command")


def source_files(root: Path) -> list[Path]:
    files = [root / name for name in SOURCE_FILES if (root / name).is_file()]
    for name in SOURCE_DIRECTORIES:
        directory = root / name
        for path in directory.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            files.append(path)
    return sorted(set(files))


def verify_bundle(bundle: Path) -> None:
    if not bundle.is_dir():
        raise RuntimeError(f"Build the binary bundle first: {bundle}")
    candidates = [p.parent for p in bundle.rglob("SOURCE_MANIFEST.toml") if "api_rest_desk" in p.parts]
    if not candidates:
        raise RuntimeError("The binary bundle is missing installed legal documents")
    legal = candidates[0]
    for name in DOCUMENTS:
        if not (legal / name).is_file() or digest(legal / name) != digest(ROOT / name):
            raise RuntimeError(f"Binary legal document is missing or stale: {name}")
    for path in (ROOT / "licenses").rglob("*"):
        if path.is_file():
            installed = legal / path.relative_to(ROOT)
            if not installed.is_file() or digest(installed) != digest(path):
                raise RuntimeError(f"Binary license missing or changed: {path.relative_to(ROOT)}")
    allowed_qt = {"qtcore", "qtgui", "qtwidgets", "qtnetwork", "qtsvg"}
    for path in bundle.rglob("*"):
        lower = path.name.lower()
        if "qpdf" in lower or "qtpdf" in lower or "qt6pdf" in lower or "opengl32sw" in lower:
            raise RuntimeError(f"An excluded unused component was bundled: {path.name}")
        # Detect new Qt modules instead of silently relying on an old license inventory.
        name = lower.removeprefix("lib").replace("qt6", "qt")
        is_qt_module = lower.startswith(("qt6", "libqt6", "qt5", "libqt5")) or (lower.startswith("qt") and lower.endswith(".framework"))
        if is_qt_module and (lower.endswith((".dll", ".dylib")) or ".so" in lower or lower.endswith(".framework")):
            module = name.split(".")[0]
            if module not in allowed_qt:
                raise RuntimeError(f"Unreviewed Qt module in bundle: {path.name}")


def verify_frozen_code(bundle: Path) -> None:
    from PyInstaller.archive.readers import CArchiveReader
    exe = bundle / ("Contents/MacOS/APIRestDesk" if sys.platform == "darwin" else "APIRestDesk.exe" if sys.platform == "win32" else "APIRestDesk")
    reader = CArchiveReader(str(exe))
    modules = reader.open_embedded_archive("PYZ.pyz")
    reviewed = tomllib.loads((ROOT / "packaging/license_sources.toml").read_text(encoding="utf-8"))["packages"]
    allowed = set(sys.stdlib_module_names) | {"api_rest_desk", "PyQt6", "_pyi_rth_utils", "typing_extensions"} | set(reviewed)
    for name in modules.toc:
        if name.split(".")[0] not in allowed:
            raise RuntimeError(f"Unreviewed Python dependency in executable: {name}")
        if not (name == "api_rest_desk" or name.startswith("api_rest_desk.")):
            continue
        source = ROOT.joinpath(*name.split("."))
        source = source / "__init__.py" if source.is_dir() else source.with_suffix(".py")
        if not source.is_file():
            raise RuntimeError(f"Matching application source is missing: {name}")
        frozen = modules.extract(name)
        current = compile(source.read_bytes(), frozen.co_filename, "exec", dont_inherit=True, optimize=0)
        if current != frozen:
            raise RuntimeError(f"Application source changed since binary build: {name}; rebuild before releasing")
    print("Frozen application code matches the current source snapshot.")


def write_binary_zip(bundle: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(bundle.rglob("*")):
            name = path.relative_to(bundle.parent).as_posix()
            if path.is_symlink():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, os.readlink(path))
            elif path.is_file():
                archive.write(path, name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, help="Path to the built application folder or macOS .app")
    parser.add_argument("--include-installer", action="store_true", help="Include a freshly compiled Windows installer")
    args = parser.parse_args()
    check()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    # Avoid importing config: it creates the user data directory as a side effect.
    # Read APP_VERSION as an AST literal, never execute the application's module during release preparation.
    import ast
    tree = ast.parse((ROOT / "api_rest_desk" / "config.py").read_text(encoding="utf-8"))
    app_version = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "APP_VERSION" for t in n.targets))
    if version != app_version:
        raise RuntimeError("APP_VERSION and project metadata disagree")
    platform = {"win32": "Windows", "darwin": "macOS"}.get(sys.platform, "Linux")
    bundle = args.bundle or ROOT / "dist" / ("APIRestDesk.app" if sys.platform == "darwin" else "APIRestDesk")
    verify_bundle(bundle)
    verify_frozen_code(bundle)
    installer = ROOT / "dist" / "installer" / f"APIRestDesk-{version}-Setup.exe"
    if args.include_installer:
        if sys.platform != "win32" or not installer.is_file():
            raise RuntimeError("Compile the matching Windows installer before including it")
        newest_payload = max(p.stat().st_mtime for p in bundle.rglob("*") if p.is_file())
        if installer.stat().st_mtime < newest_payload:
            raise RuntimeError("Installer predates the binary/legal bundle; recompile it before releasing")
    records = tomllib.loads((ROOT / "SOURCE_MANIFEST.toml").read_text(encoding="utf-8"))["sources"]
    for record in records:
        source = CACHE / record["filename"]
        if not source.is_file() or digest(source) != record["sha256"]:
            raise RuntimeError(f"Source archive missing or checksum mismatch: {record['filename']}")
    output = ROOT / "dist" / "release"
    output.mkdir(parents=True, exist_ok=True)
    prefix = f"APIRestDesk-{version}"
    app_source = output / f"{prefix}-source.zip"
    with zipfile.ZipFile(app_source, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in source_files(ROOT):
            archive.write(path, f"{prefix}-source/{path.relative_to(ROOT).as_posix()}")
    dependency_source = output / f"{prefix}-dependency-sources.zip"
    # Upstream archives are already compressed; preserve their original bytes.
    with zipfile.ZipFile(dependency_source, "w", zipfile.ZIP_STORED) as archive:
        for record in records:
            archive.write(CACHE / record["filename"], record["filename"])
        archive.write(ROOT / "SOURCE_MANIFEST.toml", "SOURCE_MANIFEST.toml")
        archive.write(ROOT / "SOURCE_CODE.md", "SOURCE_CODE.md")
    binary = output / f"{prefix}-{platform}.zip"
    write_binary_zip(bundle, binary)
    artifacts = [binary, app_source, dependency_source]
    native_inventory = output / f"{prefix}-NATIVE_INVENTORY.txt"
    native_paths = [p for p in sorted(bundle.rglob("*")) if p.is_file() and (p.suffix.lower() in (".dll", ".pyd", ".dylib") or ".so" in p.name)]
    native_inventory.write_text("Native files actually present in this bundle; SHA-256 and relative path.\nReview their provenance and licenses alongside SOURCE_MANIFEST.toml.\n\n" + "".join(f"{digest(p)}  {p.relative_to(bundle).as_posix()}\n" for p in native_paths), encoding="utf-8")
    artifacts.append(native_inventory)
    if args.include_installer:
        import shutil
        published_installer = output / installer.name
        shutil.copyfile(installer, published_installer)
        artifacts.append(published_installer)
    checksums = output / f"{prefix}-SHA256SUMS.txt"
    checksums.write_text("".join(f"{digest(path)}  {path.name}\n" for path in artifacts), encoding="utf-8")
    base = f"https://github.com/GiancaGIS/APIRestDesk/releases/download/{version}"
    notes = f"""APIRestDesk {version} is distributed under GNU GPL version 3 only (GPL-3.0-only), without warranty.

Source code for these binary downloads is available at no additional charge:
- [Matching application source]({base}/{app_source.name})
- [Dependency source archives]({base}/{dependency_source.name})
- [SHA-256 checksums]({base}/{checksums.name})

The source archives include build instructions, license texts, attribution records and a version-specific source manifest. Download both source ZIPs to obtain the corresponding sources of the application and the reviewed dependencies. Licenses and source instructions are also installed under About > Licenses and source code.

Previously granted MIT permissions on older application source copies remain in force. This release adds GPLv3 distribution notices and dependency/source materials.
"""
    (output / f"{prefix}-RELEASE_NOTES.md").write_text(notes, encoding="utf-8")
    for path in artifacts:
        print(f"Prepared {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")
    print("Prepared release notes and checksums. No files were uploaded to GitHub.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError) as error:
        print(f"Release preparation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
