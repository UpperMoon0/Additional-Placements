#!/usr/bin/env python3
"""Reject classifier/unmapped builds and stage only the remapped Forge release JAR."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import sys
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "gradle.properties"
JAR_DIR = ROOT / "forge" / "build" / "libs"
DIST = ROOT / "dist"
REQUIRED = {
    "META-INF/mods.toml",
    "com/firemerald/additionalplacements/forge/AdditionalPlacementsForge.class",
    "com/firemerald/additionalplacements/block/interfaces/forge/IForgeAdditionalPlacementBlock.class",
    "com/firemerald/additionalplacements/block/stairs/AdditionalStairBlock.class",
}

def verify(stage=False):
    match = re.search(r"(?m)^mod_version=([^\\r\\n]+)$", VERSIONS.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("Missing mod_version in gradle.properties")
    version = match.group(1).strip()
    jar = JAR_DIR / f"additionalplacements-forge-{version}.jar"
    if not jar.is_file():
        raise FileNotFoundError(f"Production remapJar missing: {jar}")
    try:
        with ZipFile(jar) as archive:
            missing = REQUIRED.difference(archive.namelist())
            if missing:
                raise ValueError(f"Missing production classes/metadata: {sorted(missing)}")
            manifest = archive.read("META-INF/mods.toml").decode("utf-8")
            if 'modId = "additionalplacements"' not in manifest:
                raise ValueError("Incorrect Forge mod ID")
            if f'version = "{version}"' not in manifest:
                raise ValueError("Forge mods.toml version is not the bumped release version")
            if archive.testzip() is not None:
                raise ValueError("Corrupted JAR member")
    except BadZipFile as error:
        raise ValueError(f"Not a valid JAR: {jar}") from error
    digest = hashlib.sha256(jar.read_bytes()).hexdigest()
    print(f"Production jar: {jar.name}, SHA256 {digest}")
    if stage:
        DIST.mkdir(exist_ok=True)
        for stale in DIST.glob("additionalplacements-forge-*.jar"):
            stale.unlink()
        shutil.copy2(jar, DIST / jar.name)
        print(f"Staged: {DIST / jar.name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", action="store_true")
    args = parser.parse_args()
    try:
        verify(stage=args.stage)
    except (OSError, ValueError) as error:
        sys.exit(str(error))
