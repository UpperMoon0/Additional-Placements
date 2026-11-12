[![Discord](https://img.shields.io/discord/176190900945289237?style=flat-square&logo=discord&logoColor=ffffff&label=Discord)](https://discord.gg/ykHRhmC)  
[![CurseForge Downloads](https://img.shields.io/curseforge/dt/674852?style=flat-square&label=Download%20on%20Curse%20%7C%20Forge)](https://www.curseforge.com/minecraft/mc-mods/additional-placements)  
[![CurseForge Downloads](https://img.shields.io/curseforge/dt/930469?style=flat-square&label=Download%20on%20Curse%20%7C%20Fabric)](https://www.curseforge.com/minecraft/mc-mods/additional-placements-fabric)  
[![Modrinth Downloads](https://img.shields.io/modrinth/dt/f5TwOKkb?style=flat-square&label=Download%20on%20Modrinth%20%7C%20Forge)](https://modrinth.com/mod/additional-placements)  
[![Modrinth Downloads](https://img.shields.io/modrinth/dt/jyJzs6EK?style=flat-square&label=Download%20on%20Modrinth%20%7C%20Fabric)](https://modrinth.com/mod/additional-placements-fabric)  

# Additional Placements
Framework and implementation for additional placement states for certain blocks

Features:  
 - no added items - additional placements are extensions of the existing slab and stair block placement logic  
 - supports slabs and stairs (vertical) and carpet and pressure plates (on walls and ceiling)
 - vertical stairs actually connnect to other stairs (and vice-versa)
 - supports most modded blocks
 - simple datagen helpers to generate blockstates, block models, and item models for modded blocks, in case extra compatibility is needed  

## Maintained fork CI

The UpperMoon0 fork uses the [central NsTut-CICD Jenkins pipeline](https://github.com/UpperMoon0/NsTut-CICD) for **both Fabric and Forge 1.20.1** builds, Forge dedicated-server regression tests, and SHA-256 verified production artifacts. The source `Jenkinsfile` is only a delegate. Its reviewed `1.20.1` default branch is the only accepted private CI source; third-party pull-request heads are never executed on private runners. The original maintainer's CurseForge/Modrinth pages linked above are not automated deployment destinations for this fork. See [Forge acceptance requirements](tests/README-forge-acceptance.md).
