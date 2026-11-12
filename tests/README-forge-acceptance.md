# Forge 1.20.1 isolated server acceptance

The source-only unit tests cannot prove the crash is gone. The GameTest in
`ForgeDelegationGameTests` uses real registered Additional Placements stairs,
converts their states, and calls `makesOpenTrapdoorAboveClimbable` on a real
dedicated-server level. The pre-fix implementation throws
`IllegalArgumentException` for missing `front_top_shape`.

Run using a **disposable workspace and world**, never the live TFG world:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
# Java 21 is used to run Loom/Gradle, targeting bytecode 17.
gradle :forge:build --no-daemon --max-workers=2 --console=plain
mkdir -p forge/run/gametest
printf 'eula=true\\n' > forge/run/gametest/eula.txt
gradle :forge:runGameTestServer --no-daemon --max-workers=2 --console=plain
python3 tests/verify_forge_jar.py --stage
```

A successful run must show the `additionalplacements.regression` GameTest
executed (not merely an exit 0 with zero tests), exit successfully and
produce `dist/additionalplacements-forge-3.0.1.2.jar`. Record the log and
SHA-256 of that exact jar. If the Loom configuration lacks the
`runGameTestServer` task, **the acceptance gate fails** and the buildscript
must be corrected; skipping the task is not acceptable.

For the reported *FowlPlay* incident, also launch a second isolated Forge
1.20.1 server with that verified production jar plus the matching FowlPlay
jar and its declared dependencies. Reproduce an open trapdoor above a ladder
next to an Additional Placements stair (include complex rotated stairs).
Let a pigeon path and tick near this setup. Confirm normal ticking without
`front_top_shape`, `Ticking entity` or recursive delegation errors. Verify
the original broken build fails the same scenario, preserving the reproduction
world/config. **Do not substitute a structural check for this compatibility
pass**. Do not use any production world, player data or live server ports.

The fork migrates CI to the reviewed `UpperMoon0/NsTut-CICD` Jenkins
library. The central pipeline tests both Fabric and Forge, runs this Forge
GameTest in an isolated workspace, verifies both remapped production JARs,
and archives exact-commit hashes and test evidence. The source Jenkinsfile
contains only the shared-library call. The fork's **reviewed default branch**
`1.20.1` is the only admitted Jenkins source; PR heads are not implicitly
allowed on private CI workers. Do not confuse unit tests with live Jenkins
acceptance or deploy an untested PR artifact.

For local/isolated acceptance, the complete pinned-tool sequence is:

```sh
python3 tools/jenkins_additional_placements.py verify
python3 tools/jenkins_additional_placements.py fabric
python3 tools/jenkins_additional_placements.py forge
python3 tools/jenkins_additional_placements.py forge-gametest
python3 tools/jenkins_additional_placements.py package
```

The runner requires Java 21 and installs only checksum-verified Gradle 8.14.
A nonzero Forge GameTest count, both production mod identities, and matching
source SHA are mandatory; the FowlPlay-specific compatibility check below
remains an additional manual release gate.

## Verified isolated result (2026-11-12 UTC)

On a disposable cloud-1 checkout, with OpenJDK 21 and cached Gradle 8.14:

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: 6 passed.
- `gradle :forge:build`: `BUILD SUCCESSFUL`, production JAR constructed.
- `python3 tests/verify_forge_jar.py --stage`: accepted only
  `additionalplacements-forge-3.0.1.2.jar`, SHA-256
  `e5ca0051d3ecc6e6d90509ef16d3bfa0c606c82edf39b5235faa77576f42b603`.
- `gradle :forge:runGameTestServer`: real Forge 47.4.18 server ran
  `additionalplacements.regression:1` and reported
  `All 1 required tests passed :)`; the test server shut down.
- Negative control: replacing the fixed receiver with the original
  `state.getBlock()` in an **uncommitted temporary working-tree edit**
  caused that same GameTest to fail with the missing
  `front_top_shape` property on `minecraft:oak_stairs`
  (`1 required tests failed :(`). The temporary edit was restored,
  verified with `git diff --quiet`. The broken code was never pushed.

The test covers the same open-trapdoor hook using a vanilla mob; **FowlPlay
itself was not installed**. The isolated FowlPlay-specific test remains a
separate pre-deployment compatibility check.

The historical GitHub Actions job was blocked at startup by account billing,
not by a Java or Forge failure. It is removed from this migration branch;
Jenkins must separately produce a successful exact-commit build and verified
artifact record before publication. No default-branch Jenkins run is claimed
for the still-unmerged PR.
