"""Collect original licenses and checksum-recorded source archives for releases.

No downloaded source is executed or extracted onto the filesystem. Network access
is explicit (--fetch-sources); subsequent checks can run entirely offline.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from importlib import metadata
import json
import posixpath
from pathlib import Path, PurePosixPath
import re
import shutil
import ssl
import sys
import tarfile
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "build" / "license-sources"
LEGAL = ROOT / "api_rest_desk" / "legal"
PROFILE = ROOT / "packaging" / "license_sources.toml"
MANIFEST = ROOT / "SOURCE_MANIFEST.toml"
DOCUMENTS = ("LICENSE", "COPYRIGHT", "THIRD_PARTY_NOTICES.md", "SOURCE_CODE.md", "SOURCE_MANIFEST.toml")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_url(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("Source downloads require HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": "APIRestDesk-license-preparation"})
    with urllib.request.urlopen(request, context=download_context(), timeout=60) as response:
        return response.read()


def download_context() -> ssl.SSLContext:
    import certifi
    context = ssl.create_default_context()
    context.load_verify_locations(cafile=certifi.where())
    return context


def download(record: dict, fetch: bool) -> Path:
    target = CACHE / record["filename"]
    if target.name != record["filename"] or not target.resolve().is_relative_to(CACHE.resolve()):
        raise ValueError("Invalid source archive filename")
    expected = record.get("sha256")
    if target.is_file() and expected and digest(target) == expected:
        return target
    if not fetch:
        raise RuntimeError(f"Missing or changed source archive: {target.name}. Run with --fetch-sources.")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".download")
    request = urllib.request.Request(record["url"], headers={"User-Agent": "APIRestDesk-license-preparation"})
    with urllib.request.urlopen(request, context=download_context(), timeout=60) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    actual = digest(temporary)
    if expected and actual != expected:
        temporary.unlink()
        raise RuntimeError(f"SHA-256 mismatch for {target.name}")
    temporary.replace(target)
    record["sha256"] = actual
    print(f"Source ready: {target.name}", flush=True)
    return target


def installed_packages(profile: dict) -> dict:
    if sys.platform == "win32" and ".".join(map(str, sys.version_info[:3])) != profile["build"]["windows_python"]:
        raise RuntimeError("Windows Python version differs from the reviewed native profile; update it before releasing")
    packages = {}
    for name, expected in profile["packages"].items():
        dist = metadata.distribution(name)
        if dist.version != expected:
            raise RuntimeError(f"{name}: installed {dist.version}, reviewed {expected}; update the profile and licenses.")
        packages[name] = dist
    # AnyIO on older supported Python versions imports this additional dependency.
    if sys.version_info < (3, 13):
        packages["typing_extensions"] = metadata.distribution("typing_extensions")
    from PyQt6.QtCore import qVersion
    if metadata.version("PyQt6-Qt6") != profile["qt"]["version"] or qVersion() != profile["qt"]["version"]:
        raise RuntimeError("Qt runtime does not match the reviewed source version")
    return packages


def source_records(profile: dict, packages: dict, fetch: bool) -> list[dict]:
    previous = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))["sources"] if MANIFEST.exists() else []
    known = {(r["name"], r["version"]): r for r in previous}
    records = []
    for name, dist in packages.items():
        key = (name, dist.version)
        if key in known:
            record = dict(known[key])
        elif fetch:
            payload = json.loads(read_url(f"https://pypi.org/pypi/{name}/{dist.version}/json"))
            candidates = [f for f in payload["urls"] if f["packagetype"] == "sdist"]
            if len(candidates) != 1:
                raise RuntimeError(f"Expected exactly one source distribution for {name} {dist.version}")
            item = candidates[0]
            record = dict(name=name, version=dist.version, filename=item["filename"], url=item["url"],
                          sha256=item["digests"]["sha256"], license=dist.metadata.get("License-Expression") or dist.metadata.get("License") or "See license files")
        else:
            raise RuntimeError(f"Source metadata missing for {name}; run with --fetch-sources")
        records.append(record)
    qt_version = profile["qt"]["version"]
    for module in profile["qt"]["modules"]:
        filename = f"{module['name']}-everywhere-src-{qt_version}.tar.xz"
        records.append(dict(name=module["name"], version=qt_version, filename=filename,
                            url=f"https://download.qt.io/official_releases/qt/{'.'.join(qt_version.split('.')[:2])}/{qt_version}/submodules/{filename}?download",
                            sha256=module["sha256"], license="See Qt and third-party license files"))
    python_version = ".".join(map(str, sys.version_info[:3]))
    match = re.match(r"OpenSSL (\d+\.\d+\.\d+)", ssl.OPENSSL_VERSION)
    if not match:
        raise RuntimeError(f"Unreviewed SSL runtime: {ssl.OPENSSL_VERSION}")
    openssl_version = match.group(1)
    for name, version, filename, url, license_id in (
        ("CPython", python_version, f"Python-{python_version}.tar.xz", f"https://www.python.org/ftp/python/{python_version}/Python-{python_version}.tar.xz", "PSF-2.0 and incorporated software licenses"),
        ("OpenSSL", openssl_version, f"openssl-{openssl_version}.tar.gz", f"https://github.com/openssl/openssl/releases/download/openssl-{openssl_version}/openssl-{openssl_version}.tar.gz", "Apache-2.0"),
    ):
        records.append(dict(known.get((name, version), dict(name=name, version=version, filename=filename, url=url, license=license_id))))
    if sys.platform == "win32":
        for native in profile.get("windows_native", ()):
            record = dict(known.get((native["name"], native["version"]), native))
            record["version_provenance"] = "Windows CPython PCbuild/python.props; review against the actual runtime when changing interpreter"
            records.append(record)
    return records


def copy_archive_notices(record: dict) -> None:
    """Retain full upstream texts and attribution records without unsafe extraction."""
    component = ROOT / "licenses" / record["name"]
    component.mkdir(parents=True, exist_ok=True)
    old_index = component / "UPSTREAM_FILES.txt"
    old_names = {line.split("\t")[0] for line in old_index.read_text(encoding="utf-8").splitlines() if "\t" in line} if old_index.exists() else set()
    with tarfile.open(CACHE / record["filename"], "r:*") as archive:
        entries = [m for m in archive.getmembers() if m.isfile()]
        references = set()
        attributions = []
        for member in entries:
            if PurePosixPath(member.name).name != "qt_attribution.json":
                continue
            content = archive.extractfile(member).read()
            try:
                data = json.loads(content, strict=False)
            except ValueError as error:
                raise RuntimeError(f"Cannot parse attribution {member.name}: {error}") from error
            for item in data if isinstance(data, list) else [data]:
                attributions.append((member.name, item))
                license_files = item.get("LicenseFile", "")
                for license_file in license_files if isinstance(license_files, list) else license_files.split():
                    references.add(posixpath.normpath(str(PurePosixPath(member.name).parent / license_file)))
        index = []
        for member in entries:
            basename = PurePosixPath(member.name).name.lower()
            is_notice = any(word in basename for word in ("license", "licence", "copying", "copyright", "notice"))
            is_notice = is_notice or any(part.lower() in ("licenses", "licences") for part in PurePosixPath(member.name).parts)
            is_notice = is_notice or basename in ("ftl.txt", "qt_attribution.json") or member.name in references
            is_notice = is_notice or (record["name"] == "CPython" and member.name.endswith("/Doc/license.rst"))
            binary_or_code = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".icns", ".svg", ".py", ".pyc", ".c", ".cpp", ".h", ".hpp", ".pm", ".pl", ".sh", ".bin", ".zip", ".gz", ".xz"}
            if PurePosixPath(member.name).suffix.lower() in binary_or_code and member.name not in references:
                is_notice = False
            if not is_notice or member.size > 2_000_000:
                continue
            # Preserve bytes; upstream paths are recorded in the index. Short filenames work on Windows.
            local_name = re.sub(r"[^A-Za-z0-9_.-]", "_", basename)[:60] + "-" + hashlib.sha256(member.name.encode()).hexdigest()[:12] + ".txt"
            (component / local_name).write_bytes(archive.extractfile(member).read())
            index.append(f"{local_name}\t{member.name}")
        if not index:
            raise RuntimeError(f"No license notices found in {record['filename']}")
        new_names = {line.split("\t")[0] for line in index}
        for name in old_names - new_names:
            obsolete = component / name
            if obsolete.name != name or not obsolete.resolve().is_relative_to((ROOT / "licenses").resolve()):
                raise ValueError("Invalid generated notice path")
            obsolete.unlink(missing_ok=True)
        (component / "UPSTREAM_FILES.txt").write_text("Original files from " + record["url"] + "\n\n" + "\n".join(sorted(index)) + "\n", encoding="utf-8")
        if attributions:
            text = "Qt attribution records from the exact source release; some components may not be compiled into this binary.\n\n"
            for origin, item in attributions:
                text += origin + "\n" + json.dumps(item, ensure_ascii=False, indent=2) + "\n\n"
            (component / "ATTRIBUTIONS.txt").write_text(text, encoding="utf-8")


def write_manifest(records: list[dict]) -> None:
    lines = ["# Source archives retained for the reviewed local build.", "# SHA-256 comes from PyPI/Qt for those packages; other native digests record HTTPS downloads."]
    for record in records:
        lines += ["", "[[sources]]"]
        lines += [f"{key} = {json.dumps(str(value), ensure_ascii=False)}" for key, value in record.items()]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_notices(records: list[dict]) -> None:
    lines = ["# Third-party notices", "", "APIRestDesk is Copyright (c) 2026 GiancaGIS, licensed under GPL-3.0-only.",
             "Dependency copyrights and license terms remain with their respective authors.",
             "The original upstream texts and attribution records are provided in `licenses/`.", "",
             "PyQt6: Copyright (c) 2026 Riverbank Computing Limited; GNU GPL version 3 only.",
             "Qt: Copyright The Qt Company Ltd. and other contributors; distributed using the applicable LGPLv3 permissions. See the module licenses and embedded third-party notices.",
             "Qt and Python trademarks belong to their respective owners; no endorsement is implied.", "",
             "| Component | Reviewed version | License / notices |", "| --- | --- | --- |"]
    for record in records:
        lines.append(f"| {record['name']} | {record['version']} | {record['license']} — `licenses/{record['name']}/` |")
    qt = metadata.distribution("PyQt6-Qt6")
    lines.append(f"| PyQt6-Qt6 wheel | {qt.version} | LGPLv3 — `licenses/PyQt6-Qt6/`; source is provided by the Qt module archives above |")
    lines += ["", "Qt notices include upstream third-party license texts and attribution records for Qt Base, SVG, and Image Formats. See each `UPSTREAM_FILES.txt` for their original paths.",
              "Qt PDF and the software OpenGL fallback are excluded from the application bundle because APIRestDesk does not use them.",
              "PyInstaller's exception permits generated bundles under other licenses when dependency terms are met; it does not remove PyQt/Qt obligations.",
              "Certifi's CA bundle retains MPL-2.0 notices; MPL applies to the covered files.",
              "On Windows, Microsoft runtime components retain Microsoft's terms, separately from the GPL application; see the Python distribution notice in `licenses/CPython/WINDOWS_DISTRIBUTION_LICENSE.txt`.",
              "The compiler and libraries used by Inno Setup retain their own notices. Where available, the installed Inno Setup license is included in `licenses/InnoSetup/`.",
              "The previous APIRestDesk MIT notice concerns previously licensed copies, not the current overall application's license.",
              "", "Source locations and SHA-256 values are recorded in `SOURCE_MANIFEST.toml`. For obtaining, rebuilding and modifying the release, see `SOURCE_CODE.md`.",
              "These files document the reviewed build; a new dependency, native module, runtime or platform requires an updated inventory."]
    (ROOT / "THIRD_PARTY_NOTICES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_legal() -> None:
    LEGAL.mkdir(parents=True, exist_ok=True)
    expected = {Path(name) for name in DOCUMENTS}
    expected.update(path.relative_to(ROOT) for path in (ROOT / "licenses").rglob("*") if path.is_file())
    for path in LEGAL.rglob("*"):
        if path.is_file() and path.relative_to(LEGAL) not in expected:
            if not path.resolve().is_relative_to(LEGAL.resolve()) or not LEGAL.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError("Invalid generated legal bundle path")
            path.unlink()
    for name in DOCUMENTS:
        shutil.copyfile(ROOT / name, LEGAL / name)
    shutil.copytree(ROOT / "licenses", LEGAL / "licenses", dirs_exist_ok=True)


def check() -> None:
    profile = tomllib.loads(PROFILE.read_text(encoding="utf-8"))
    packages = installed_packages(profile)
    if not MANIFEST.exists():
        raise RuntimeError("Prepare the license bundle first")
    recorded = {(r["name"], r["version"]) for r in tomllib.loads(MANIFEST.read_text(encoding="utf-8"))["sources"]}
    for record in source_records(profile, packages, False):
        if (record["name"], record["version"]) not in recorded:
            raise RuntimeError(f"Source manifest mismatch: {record['name']}")
    for name in DOCUMENTS:
        if not (LEGAL / name).is_file() or digest(ROOT / name) != digest(LEGAL / name):
            raise RuntimeError(f"Packaged legal document is missing or stale: {name}")
    for path in (ROOT / "licenses").rglob("*"):
        if path.is_file():
            target = LEGAL / path.relative_to(ROOT)
            if not target.is_file() or digest(target) != digest(path):
                raise RuntimeError(f"Packaged notice is missing or stale: {path.relative_to(ROOT)}")
    print("Legal bundle and reviewed dependency versions match.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-sources", action="store_true", help="Fetch missing archives from upstream via HTTPS")
    parser.add_argument("--check", action="store_true", help="Validate the packaged legal bundle without changing files or accessing the network")
    args = parser.parse_args()
    if args.check:
        check()
        return
    profile = tomllib.loads(PROFILE.read_text(encoding="utf-8"))
    packages = installed_packages(profile)
    records = source_records(profile, packages, args.fetch_sources)
    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda r: download(r, args.fetch_sources), records))
    for record in records:
        copy_archive_notices(record)
    license_packages = {**packages, "PyQt6-Qt6": metadata.distribution("PyQt6-Qt6")}
    for name, dist in license_packages.items():
        component = ROOT / "licenses" / name
        component.mkdir(parents=True, exist_ok=True)
        license_files = [f for f in dist.files or () if any(s in str(f).lower() for s in ("license", "copying", "notice")) and ".dist-info/" in str(f)]
        if not license_files:
            raise RuntimeError(f"Installed license metadata missing: {name}")
        for i, file in enumerate(license_files):
            shutil.copyfile(dist.locate_file(file), component / f"INSTALLED-{i}-{Path(file).name}.txt")
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if sys.platform == "win32":
        if not python_license.is_file():
            raise RuntimeError("The original Windows Python distribution license is required")
        shutil.copyfile(python_license, ROOT / "licenses" / "CPython" / "WINDOWS_DISTRIBUTION_LICENSE.txt")
        inno = Path(__import__('os').environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Inno Setup 6" / "license.txt"
        if inno.is_file():
            folder = ROOT / "licenses" / "InnoSetup"
            folder.mkdir(exist_ok=True)
            shutil.copyfile(inno, folder / "LICENSE.txt")
    mpl = ROOT / "licenses" / "certifi" / "MPL-2.0.txt"
    if not mpl.is_file():
        if not args.fetch_sources:
            raise RuntimeError("Missing full MPL-2.0 text; run with --fetch-sources")
        mpl.write_bytes(read_url("https://www.mozilla.org/media/MPL/2.0/index.txt"))
    write_manifest(records)
    write_notices(records)
    sync_legal()
    check()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError) as error:
        print(f"License preparation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
