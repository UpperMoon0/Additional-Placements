package com.firemerald.additionalplacements.forge;

import com.firemerald.additionalplacements.AdditionalPlacementsMod;
import com.firemerald.additionalplacements.block.stairs.AdditionalStairBlock;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.TrapDoorBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraftforge.gametest.GameTestHolder;
import net.minecraftforge.gametest.PrefixGameTestTemplate;

/**
 * Runs in a real Forge dedicated-server GameTest process, not a mock JVM.
 * Reproduces the exact converted stair-state dispatch that used to throw for
 * a missing "front_top_shape" property when a mob checks an open trapdoor.
 */
@GameTestHolder(AdditionalPlacementsMod.MOD_ID)
@PrefixGameTestTemplate(false)
public final class ForgeDelegationGameTests {
    private ForgeDelegationGameTests() {}

    @GameTest(template = "delegation_empty", batch = "additionalplacements.regression")
    public static void stairTrapdoorClimbability(GameTestHelper helper) {
        BlockPos local = new BlockPos(1, 1, 1);
        BlockPos worldPos = helper.absolutePos(local);
        BlockState trapdoor = Blocks.OAK_TRAPDOOR.defaultBlockState()
                .setValue(TrapDoorBlock.OPEN, true);
        BlockPos trapdoorLocal = local.below();
        helper.setBlock(trapdoorLocal, trapdoor);
        LivingEntity simulatedMob = EntityType.CHICKEN.create(helper.getLevel());
        if (simulatedMob == null) {
            helper.fail("Cannot create test mob for trapdoor ladder path");
            return;
        }
        simulatedMob.moveTo(worldPos.getX() + 0.5, worldPos.getY() - 0.5,
                worldPos.getZ() + 0.5);
        int checked = 0;

        for (Block block : BuiltInRegistries.BLOCK) {
            if (!(block instanceof AdditionalStairBlock stair)) continue;

            helper.setBlock(local, stair.defaultBlockState());
            BlockState actualState = helper.getLevel().getBlockState(worldPos);
            BlockState parentState = stair.getModelState(actualState);
            if (parentState.getBlock() == stair) {
                helper.fail("The converted stair still delegates to the wrapper: " + block);
                return;
            }

            // Old code redispatched through actualState.getBlock() while passing
            // parentState. That recursed into getModelState and failed before return.
            boolean expected = parentState.getBlock().makesOpenTrapdoorAboveClimbable(
                    parentState, helper.getLevel(), worldPos, trapdoor);
            boolean actual = actualState.getBlock().makesOpenTrapdoorAboveClimbable(
                    actualState, helper.getLevel(), worldPos, trapdoor);
            if (actual != expected) {
                helper.fail("Trapdoor climbability mismatch for " + block);
                return;
            }
            // Mirror FowlPlay's entry path through the open trapdoor hook.
            trapdoor.getBlock().isLadder(trapdoor, helper.getLevel(),
                    helper.absolutePos(trapdoorLocal), simulatedMob);
            checked++;
        }

        if (checked == 0) {
            helper.fail("No generated Additional Placements stairs were registered");
            return;
        }
        helper.succeed();
    }
}
