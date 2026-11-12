"""Production release selection must exclude all non-remapped JAR variants."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

SOURCE = Path(__file__).with_name("verify_forge_jar.py")
SPEC = importlib.util.spec_from_file_location("verify_forge_jar", SOURCE)
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class JarSelectionTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.gradle = root / "gradle.properties"
        self.gradle.write_text("mod_version=3.0.1.2\n", encoding="utf-8")
        self.libs = root / "forge" / "build" / "libs"
        self.libs.mkdir(parents=True)
        self.dist = root / "dist"
        for attr, value in (("VERSIONS", self.gradle), ("JAR_DIR", self.libs), ("DIST", self.dist)):
            p = patch.object(VERIFIER, attr, value)
            p.start()
            self.addCleanup(p.stop)

    def jar(self, name, valid=True, version="3.0.1.2"):
        output = self.libs / name
        with ZipFile(output, "w") as z:
            z.writestr("META-INF/mods.toml", f'modId = "additionalplacements"\nversion = "{version}"\n')
            if valid:
                for member in VERIFIER.REQUIRED - {"META-INF/mods.toml"}:
                    z.writestr(member, b"fixture")
        return output

    def test_stages_exact_production_jar_only(self):
        self.jar("additionalplacements-forge-3.0.1.2-sources.jar")
        self.jar("additionalplacements-forge-3.0.1.2-dev-shadow.jar")
        production = self.jar("additionalplacements-forge-3.0.1.2.jar")
        with contextlib.redirect_stdout(io.StringIO()):
            VERIFIER.verify(stage=True)
        self.assertEqual([p.name for p in self.dist.iterdir()], [production.name])
        self.assertEqual((self.dist / production.name).read_bytes(), production.read_bytes())

    def test_rejects_sources_without_production(self):
        self.jar("additionalplacements-forge-3.0.1.2-sources.jar")
        with self.assertRaises(FileNotFoundError):
            VERIFIER.verify(stage=True)

    def test_rejects_missing_classes(self):
        self.jar("additionalplacements-forge-3.0.1.2.jar", valid=False)
        with self.assertRaisesRegex(ValueError, "Missing production classes"):
            VERIFIER.verify()

    def test_rejects_wrong_embedded_version(self):
        self.jar("additionalplacements-forge-3.0.1.2.jar", version="3.0.1.1")
        with self.assertRaisesRegex(ValueError, "version"):
            VERIFIER.verify()


if __name__ == "__main__":
    unittest.main()
