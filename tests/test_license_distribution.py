from pathlib import Path
import sys
import io
import tarfile
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import prepare_licenses as licenses
import prepare_release_sources as release


class SourceArchiveTest(unittest.TestCase):
    def test_spdx_license_names_and_attributions_are_collected_from_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "build" / "license-sources"
            cache.mkdir(parents=True)
            path = cache / "qtbase.tar.gz"
            contents = {
                "qtbase/LICENSES/LGPL-3.0-only.txt": b"full LGPL text",
                "qtbase/src/qt_attribution.json": b'{"Name":"Embedded library","LicenseFile":"LICENSE"}',
                "qtbase/src/LICENSE": b"library notice",
                "qtbase/src/COPYING.LGPLv2.1": b"license with an unusual suffix",
                "qtbase/docs/license.png": b"not a text notice",
            }
            with tarfile.open(path, "w:gz") as archive:
                for name, content in contents.items():
                    entry = tarfile.TarInfo(name)
                    entry.size = len(content)
                    archive.addfile(entry, io.BytesIO(content))
            with patch.object(licenses, "ROOT", root), patch.object(licenses, "CACHE", cache):
                licenses.copy_archive_notices(dict(name="qtbase", filename=path.name, url="https://example.org/qtbase.tar.gz"))
            texts = [p.read_bytes() for p in (root / "licenses" / "qtbase").glob('*.txt')]
            self.assertIn(b"full LGPL text", texts)
            self.assertIn(b"library notice", texts)
            self.assertIn(b"license with an unusual suffix", texts)
            self.assertNotIn(b"not a text notice", texts)

    def test_source_snapshot_includes_code_but_excludes_local_data_and_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "api_rest_desk").mkdir()
            (root / "api_rest_desk" / "main_window.py").write_text("# code")
            (root / "api_rest_desk" / "private.json").write_text('{"token": "private"}')
            (root / "api_rest_desk" / ".env").write_text("TOKEN=private")
            (root / "rest_client_settings.json").write_text('{"password": "private"}')
            (root / ".venv").mkdir()
            (root / ".venv" / "unrelated.py").write_text("# excluded")
            (root / "LICENSE").write_text("license")
            selected = {str(p.relative_to(root)).replace("\\", "/") for p in release.source_files(root)}
            self.assertEqual(selected, {"LICENSE", "api_rest_desk/main_window.py"})

    def test_cached_archive_must_match_its_checksum(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(licenses, "CACHE", Path(directory)):
            (Path(directory) / "source.tar.gz").write_bytes(b"changed")
            record = dict(filename="source.tar.gz", sha256="0" * 64, url="https://example.org/source.tar.gz")
            with self.assertRaisesRegex(RuntimeError, "Missing or changed"):
                licenses.download(record, fetch=False)

    def test_download_cannot_escape_source_cache(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(licenses, "CACHE", Path(directory)):
            with self.assertRaisesRegex(ValueError, "Invalid source archive"):
                licenses.download(dict(filename="../outside.tar.gz"), fetch=False)


class BinaryNoticesTest(unittest.TestCase):
    def test_missing_notices_prevent_release_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "missing installed legal"):
                release.verify_bundle(Path(directory))

    def test_binary_documents_must_match_source_and_unused_modules_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "dist" / "APIRestDesk"
            legal = bundle / "_internal" / "api_rest_desk" / "legal"
            legal.mkdir(parents=True)
            (root / "licenses").mkdir()
            for name in licenses.DOCUMENTS:
                (root / name).write_text(name)
                (legal / name).write_text(name)
            with patch.object(release, "ROOT", root):
                release.verify_bundle(bundle)
                (legal / "LICENSE").write_text("stale")
                with self.assertRaisesRegex(RuntimeError, "stale: LICENSE"):
                    release.verify_bundle(bundle)
                (legal / "LICENSE").write_text("LICENSE")
                (bundle / "Qt6Pdf.dll").write_bytes(b"unused")
                with self.assertRaisesRegex(RuntimeError, "excluded unused component"):
                    release.verify_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
