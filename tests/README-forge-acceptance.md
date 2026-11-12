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

GitHub Actions jobs that fail before the checkout step and report an empty
`steps` list cannot establish anything about Java/Gradle. Check GitHub
Actions billing/usage limits, hosted runner entitlement and repository
Actions policy in GitHub settings. Only a successfully executed exact-HEAD
run, or independently recorded equivalent isolated acceptance, counts.
