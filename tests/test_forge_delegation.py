"""Regression guard for Forge delegation of adapted block states.

This catches a server-fatal bug where a wrapper block redispatched to itself
with a vanilla parent BlockState, losing the front_top_shape property.

It is a structural guard; a Forge GameTest/real-player acceptance test is
still required before publishing or deploying a release.
"""
from pathlib import Path
import re
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "forge/src/main/java/com/firemerald/additionalplacements/block/interfaces/forge/"
    / "IForgeAdditionalPlacementBlock.java"
)


def method_body(name: str) -> str:
    source = SOURCE.read_text(encoding="utf-8")
    match = re.search(r"\\bdefault\\s+\\S+\\s+" + re.escape(name) + r"\\s*\\(", source)
    if match is None:
        raise AssertionError(f"Missing Forge method {name}")
    opening = source.find("{", match.end())
    if opening < 0:
        raise AssertionError(f"Missing method body: {name}")
    depth = 1
    for index in range(opening + 1, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : index]
    raise AssertionError(f"Unterminated method body: {name}")


class ConvertedBlockStateDelegationTest(unittest.TestCase):
    def test_trapdoor_climbability_never_recurses_into_wrapper(self):
        body = method_body("makesOpenTrapdoorAboveClimbable")
        self.assertIn("BlockState modelState = getModelState(state);", body)
        self.assertIn(
            "modelState.getBlock().makesOpenTrapdoorAboveClimbable(modelState, level, pos, trapdoorState)",
            body,
        )
        self.assertNotIn("state.getBlock().makesOpenTrapdoorAboveClimbable", body)

    def test_other_parent_delegations_use_converted_state(self):
        for name in ("isSlimeBlock", "isStickyBlock", "getPistonPushReaction"):
            with self.subTest(method=name):
                body = method_body(name)
                self.assertIn("BlockState modelState = getModelState(state);", body)
                self.assertIn(f"modelState.getBlock().{name}(modelState)", body)
                self.assertNotIn(f"{name}(state)", body)


if __name__ == "__main__":
    unittest.main()
