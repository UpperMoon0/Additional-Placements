"""Offline CI contracts: no live world, no Gradle download, no Jenkins needed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

SOURCE = Path(__file__).resolve().parents[1] / "tools" / "jenkins_additional_placements.py"
spec = importlib.util.spec_from_file_location("additional_ci", SOURCE)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class AdditionalPlacementsCIContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patcher = patch.object(ci, "ROOT", self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        (self.root / "gradle.properties").write_text("mod_version=3.0.1.2\n")

    def jar(self, loader, valid=True):
        name = f"additionalplacements-{loader}-3.0.1.2.jar"
        directory = self.root / ("fabric/build/libs" if loader == "fabric" else "dist")
        directory.mkdir(parents=True, exist_ok=True)
        jar = directory / name
        with ZipFile(jar, "w") as bundle:
            if loader == "fabric":
                bundle.writestr("fabric.mod.json", json.dumps({
                    "id": "additionalplacements" if valid else "wrongmod", "version": "3.0.1.2"
                }))
                for member in (
                    "com/firemerald/additionalplacements/common/fabric/FabricModEvents.class",
                    "com/firemerald/additionalplacements/client/fabric/FabricModEvents.class",
                    "com/firemerald/additionalplacements/generation/APGenerationTypes.class",
                    "additionalplacements.accesswidener",
                    "mixins.additionalplacements.json",
                ):
                    bundle.writestr(member, b"fixture")
            else:
                bundle.writestr("META-INF/mods.toml",
                                'modId = "additionalplacements"\nversion = "' +
                                ("3.0.1.2" if valid else "3.0.1.1") + '"\n')
        return jar

    def proof(self, sha):
        directory = self.root / "ci-evidence"
        directory.mkdir()
        (directory / "gametest.json").write_text(json.dumps({
            "source_sha": sha, "batch": "additionalplacements.regression",
            "required_tests": 1, "result": "passed",
        }))

    def test_only_expected_production_jar_identity_is_accepted(self):
        self.jar("fabric")
        self.jar("forge")
        ci.verify_jar(self.root / "fabric/build/libs/additionalplacements-fabric-3.0.1.2.jar",
                      "fabric.mod.json", "3.0.1.2")
        ci.verify_jar(self.root / "dist/additionalplacements-forge-3.0.1.2.jar",
                      "META-INF/mods.toml", "3.0.1.2")
        for loader, metadata in (("fabric", "fabric.mod.json"), ("forge", "META-INF/mods.toml")):
            jar = self.jar(loader, valid=False)
            with self.assertRaisesRegex(RuntimeError, "identity/version"):
                ci.verify_jar(jar, metadata, "3.0.1.2")
        with self.assertRaisesRegex(RuntimeError, "missing"):
            ci.verify_jar(self.root / "dist/additionalplacements-forge-3.0.1.2-sources.jar",
                          "META-INF/mods.toml", "3.0.1.2")

    def test_missing_or_stale_game_test_proof_blocks_packaging(self):
        sha = "a" * 40
        with patch.object(ci, "commit_sha", return_value=sha):
            with self.assertRaisesRegex(RuntimeError, "No dedicated-server"):
                ci.package()
            self.proof("b" * 40)
            with self.assertRaisesRegex(RuntimeError, "exact checkout"):
                ci.package()

    def test_both_loaders_and_provenance_are_archived_only_after_proof(self):
        sha = "a" * 40
        self.proof(sha)
        fabric = self.jar("fabric")
        forge = self.jar("forge")
        with patch.object(ci, "commit_sha", return_value=sha), patch.object(ci, "run"):
            ci.package()
        out = self.root / "ci-production"
        self.assertEqual(
            {x.name for x in out.iterdir()},
            {fabric.name, forge.name, "provenance.json", "SHA256SUMS"},
        )
        proof = json.loads((out / "provenance.json").read_text())
        self.assertEqual(proof["source_sha"], sha)
        self.assertEqual(proof["loaders"], ["fabric", "forge"])
        self.assertEqual(proof["forge_gametest"]["result"], "passed")
        manifest = (out / "SHA256SUMS").read_text()
        for name in (fabric.name, forge.name, "provenance.json"):
            self.assertIn(name, manifest)

    def test_zero_tests_and_missing_batch_fail_closed(self):
        with patch.object(ci, "gradle", side_effect=lambda *args, log: (
                log.parent.mkdir(parents=True, exist_ok=True),
                log.write_text("BUILD SUCCESSFUL\nAll 0 required tests passed :)\n"))):
            with self.assertRaisesRegex(RuntimeError, "did not execute"):
                ci.forge_gametest()

    def test_valid_real_server_log_produces_exact_sha_evidence(self):
        sha = "a" * 40
        fixture = "Running test batch 'additionalplacements.regression:1'\nAll 1 required tests passed :)\n"
        with patch.object(ci, "gradle", side_effect=lambda *args, log: (
                log.parent.mkdir(parents=True, exist_ok=True), log.write_text(fixture))), \
             patch.object(ci, "commit_sha", return_value=sha):
            ci.forge_gametest()
        self.assertEqual(json.loads((self.root / "ci-evidence/gametest.json").read_text())["source_sha"], sha)
        self.assertEqual((self.root / "forge/run/gametest/eula.txt").read_text(), "eula=true\n")
        settings = (self.root / "forge/run/gametest/server.properties").read_text()
        self.assertIn("server-ip=127.0.0.1", settings)
        self.assertIn("server-port=0", settings)


if __name__ == "__main__":
    unittest.main()
