"""Archive handling tests using synthetic inputs; no application files required."""
import hashlib
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("local_builder", ROOT / "build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ArchiveInputTests(unittest.TestCase):
    def test_extraction_preserves_input_and_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "input.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("nested/readme.txt", "example")
            checksum = hashlib.sha256(archive.read_bytes()).digest()
            builder.extract_linux_archive(archive, root / "extracted")
            self.assertEqual((root / "extracted/nested/readme.txt").read_text(), "example")
            self.assertEqual(hashlib.sha256(archive.read_bytes()).digest(), checksum)

    def test_traversal_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "input.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("safe.txt", "example")
                output.writestr("../outside.txt", "escape")
            with self.assertRaises(ValueError):
                builder.extract_linux_archive(archive, root / "extracted")
            self.assertFalse((root / "outside.txt").exists())
            self.assertFalse((root / "extracted/safe.txt").exists())

    def test_absolute_path_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "input.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("/absolute.txt", "example")
            with self.assertRaises(ValueError):
                builder.extract_linux_archive(archive, root / "extracted")

    def test_symbolic_link_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "input.zip"
            item = zipfile.ZipInfo("link")
            item.create_system = 3
            item.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr(item, "../outside")
            with self.assertRaises(ValueError):
                builder.extract_linux_archive(archive, root / "extracted")

    def test_case_collisions_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "input.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(archive, "w") as output:
                    output.writestr("Readme.txt", "first")
                    output.writestr("readme.txt", "second")
            with self.assertRaises(ValueError):
                builder.extract_linux_archive(archive, root / "extracted")


if __name__ == "__main__":
    unittest.main()
