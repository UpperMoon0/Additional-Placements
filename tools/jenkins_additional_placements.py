#!/usr/bin/env python3
"""Portable, fail-closed build commands called by NsTut-CICD's reviewed pipeline.

Only the central Jenkins library controls which stages run, their timeouts,
worker admission and artifact publication. No live Minecraft world is touched.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "8.14"
DISTRIBUTION_SHA = "61ad310d3c7d3e5da131b76bbf22b5a4c0786e9d892dae8c1658d4b484de3caa"
DISTRIBUTION_URL = "https://services.gradle.org/distributions/gradle-8.14-bin.zip"
PHASES = ("verify", "fabric", "forge", "forge-gametest", "package")
TARGETS = ("fabric", "forge")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def java_environment():
    home = os.environ.get("JAVA_HOME_21") or os.environ.get("JAVA_HOME")
    if not home:
        raise RuntimeError("CI requires a qualified Java 21 toolchain")
    binary = Path(home) / "bin" / ("java.exe" if os.name == "nt" else "java")
    if not binary.is_file():
        raise RuntimeError("Java 21 executable missing from reviewed toolchain")
    info = subprocess.run([str(binary), "-version"], capture_output=True, text=True, check=True)
    if not re.search(r'(?:openjdk|java) version "21(?:[.+"]|$)', info.stderr + info.stdout):
        raise RuntimeError("CI requires Java 21 (not Java 17 or an unspecified PATH Java)")
    env = os.environ.copy()
    env["JAVA_HOME"] = home
    env["PATH"] = str(binary.parent) + os.pathsep + env.get("PATH", "")
    env["ORG_GRADLE_PROJECT_org.gradle.java.installations.auto-detect"] = "false"
    return env


def gradle_binary():
    # Use the same checksum-pinned distribution on both Windows and Linux.
    home = Path.home() / ".cache" / "nstut-ci" / "gradle-8.14"
    executable = home / "gradle-8.14" / "bin" / ("gradle.bat" if os.name == "nt" else "gradle")
    marker = home / "distribution.sha256"
    if executable.is_file() and marker.is_file() and marker.read_text().strip() == DISTRIBUTION_SHA:
        return str(executable)
    home.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gradle-download-", dir=home.parent) as temp:
        archive = Path(temp) / "gradle.zip"
        with urlopen(DISTRIBUTION_URL, timeout=90) as response, archive.open("wb") as target:
            shutil.copyfileobj(response, target, 1024 * 1024)
        if sha256(archive) != DISTRIBUTION_SHA:
            raise RuntimeError("Downloaded Gradle 8.14 did not match the reviewed SHA-256")
        staged = Path(temp) / "install"
        staged.mkdir()
        with ZipFile(archive) as zf:
            for member in zf.infolist():
                dest = (staged / member.filename).resolve()
                if not dest.is_relative_to(staged.resolve()) or not member.filename.startswith("gradle-8.14/"):
                    raise RuntimeError("Unsafe Gradle archive path")
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise RuntimeError("Unexpected symlink in Gradle archive")
            zf.extractall(staged)
        candidate = staged / "gradle-8.14" / "bin" / executable.name
        if not candidate.is_file():
            raise RuntimeError("Gradle distribution missing launcher")
        if os.name != "nt":
            candidate.chmod(candidate.stat().st_mode | 0o111)
        (staged / "distribution.sha256").write_text(DISTRIBUTION_SHA + "\n")
        # A worker has one executor, so installation is serialized per worker.
        if home.exists():
            shutil.rmtree(home)
        staged.replace(home)
    return str(executable)


def run(command, env=None, log=None):
    command = [str(x) for x in command]
    if log is None:
        subprocess.run(command, cwd=ROOT, env=env, check=True)
        return
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as stream:
        with subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, errors="replace") as process:
            for line in process.stdout:
                sys.stdout.write(line)
                stream.write(line)
            if process.wait():
                raise RuntimeError("Required dedicated-server GameTest failed")


def gradle(*tasks, log=None):
    env = java_environment()
    run([gradle_binary(), *tasks, "--no-daemon", "--max-workers=2", "--console=plain"], env, log)


def commit_sha():
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not re.fullmatch(r"[a-f0-9]{40}", sha):
        raise RuntimeError("Unverifiable source revision")
    expected = os.environ.get("GIT_COMMIT")
    if expected and expected != sha:
        raise RuntimeError("Jenkins checkout SHA does not match source revision")
    return sha


def mod_version():
    data = (ROOT / "gradle.properties").read_text(encoding="utf-8")
    matches = re.findall(r"^mod_version=([A-Za-z0-9.+_-]+)$", data, flags=re.MULTILINE)
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one mod_version")
    return matches[0]


def verify_jar(path, metadata, version):
    if not path.is_file():
        raise RuntimeError("Required remapped production JAR missing: " + path.name)
    with ZipFile(path) as jar:
        if jar.testzip() is not None:
            raise RuntimeError("Damaged production JAR: " + path.name)
        if metadata not in jar.namelist():
            raise RuntimeError("Required loader metadata missing: " + path.name)
        if metadata == "fabric.mod.json":
            doc = json.loads(jar.read(metadata))
            if doc.get("id") != "additionalplacements" or doc.get("version") != version:
                raise RuntimeError("Incorrect Fabric mod identity/version")
        else:
            text = jar.read(metadata).decode("utf-8")
            if 'modId = "additionalplacements"' not in text or f'version = "{version}"' not in text:
                raise RuntimeError("Incorrect Forge mod identity/version")


def forge_gametest():
    root = ROOT / "forge" / "run" / "gametest"
    root.mkdir(parents=True, exist_ok=True)
    (root / "eula.txt").write_text("eula=true\n")
    log = ROOT / "ci-evidence" / "forge-gametest.log"
    gradle(":forge:runGameTestServer", log=log)
    data = log.read_text(encoding="utf-8")
    batch = re.search(r"Running test batch 'additionalplacements\.regression:([1-9]\d*)", data)
    passed = re.search(r"All ([1-9]\d*) required tests passed", data)
    if not batch or not passed or int(batch.group(1)) != int(passed.group(1)):
        raise RuntimeError("Dedicated server did not execute and pass the required Forge regression batch")
    (ROOT / "ci-evidence" / "gametest.json").write_text(json.dumps({
        "source_sha": commit_sha(), "batch": "additionalplacements.regression",
        "required_tests": int(passed.group(1)), "result": "passed"
    }, sort_keys=True) + "\n")


def package():
    sha = commit_sha()
    version = mod_version()
    proof = ROOT / "ci-evidence" / "gametest.json"
    if not proof.is_file():
        raise RuntimeError("No dedicated-server GameTest acceptance proof")
    result = json.loads(proof.read_text(encoding="utf-8"))
    if result != {"source_sha": sha, "batch": "additionalplacements.regression",
                  "required_tests": result.get("required_tests"), "result": "passed"} or result["required_tests"] < 1:
        raise RuntimeError("GameTest evidence does not match this exact checkout")
    # The existing strict Forge verifier rejects sources/dev-shadow variants.
    run([sys.executable, "tests/verify_forge_jar.py", "--stage"])
    jars = {
        "fabric": ROOT / "fabric" / "build" / "libs" / f"additionalplacements-fabric-{version}.jar",
        "forge": ROOT / "dist" / f"additionalplacements-forge-{version}.jar",
    }
    verify_jar(jars["fabric"], "fabric.mod.json", version)
    verify_jar(jars["forge"], "META-INF/mods.toml", version)
    target = ROOT / "ci-production"
    target.mkdir(exist_ok=True)
    for stale in target.iterdir():
        if stale.is_file():
            stale.unlink()
    checksums = []
    for loader in TARGETS:
        path = jars[loader]
        shutil.copy2(path, target / path.name)
        checksums.append(f"{sha256(path)}  {path.name}")
    (target / "provenance.json").write_text(json.dumps({
        "schema": 1, "repository": "UpperMoon0/Additional-Placements",
        "source_sha": sha, "version": version, "loaders": list(TARGETS),
        "forge_gametest": result,
    }, sort_keys=True, indent=2) + "\n")
    checksums.append(f"{sha256(target / 'provenance.json')}  provenance.json")
    (target / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
    print("Verified exact-SHA Forge and Fabric production artifacts:", sha)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in PHASES:
        raise SystemExit("Usage: jenkins_additional_placements.py " + "|".join(PHASES))
    stage = sys.argv[1]
    if stage == "verify":
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"])
    elif stage == "fabric":
        gradle(":fabric:build")
    elif stage == "forge":
        gradle(":forge:build")
    elif stage == "forge-gametest":
        forge_gametest()
    else:
        package()


if __name__ == "__main__":
    main()
