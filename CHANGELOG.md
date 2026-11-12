# 3.0.1.2 (Forge 1.20.1 hotfix candidate)

- Fix a dedicated-server crash when a mob checks ladder/trapdoor climbability against an Additional Placements stair: delegate to the vanilla parent block using its converted state, rather than recursively calling the wrapper.
- Correct converted-state delegation for slime, sticky-block and piston push-reaction hooks.
- Add a dedicated-server Forge GameTest reproducing the converted stair/trapdoor hook; structural Python regression checks remain as a fast supplementary guard.
- CI verifies and stages only the remapped production Forge JAR. Sources and dev-shadow JARs are excluded.

**Release gate:** Do not publish or deploy to a live world until the exact-commit Forge GameTest completes successfully, the production binary is verified, and the isolated FowlPlay compatibility scenario is exercised. These checks are not claimed as passed merely by adding them.
