# Silksong Atlas — a TOME map pack

An unofficial, fan-made map pack for **Hollow Knight: Silksong**, for the
[TOME](https://github.com/rahulskann/tome) offline map app.

> Not affiliated with or endorsed by Team Cherry. This pack is free and always will be.
> If you represent Team Cherry and would like it changed or removed, open an issue and
> it will be taken down promptly.

## Contents

| Map | Source |
| --- | --- |
| Pharloom (world overview) | In-game map screenshot |
| Bone Bottom & Moss Grotto | In-game map screenshot |

Marker categories: regions, areas, benches, Bellways, Mask Shards, Spool Fragments,
Crests, Tools, Craftmetal, Memory Lockets, Lost Fleas.

## Credits and licences

- **Map art** is from *Hollow Knight: Silksong* © Team Cherry, captured from the game
  by the pack author. It is **not** covered by the licence below.
- **Marker data** (`markers/*.json`: names, positions, descriptions) is licensed
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Some descriptions may
  be adapted from the [Hollow Knight Wiki](https://hollowknight.wiki) (CC BY-SA 3.0);
  such entries say so in their description.

## Building

Tiles are built from `source/` with TOME's slicer and are not committed:

    python ../../tome/tools/slicer/slice_map.py source/world.png out --map-id world --zip
    python ../../tome/tools/slicer/slice_map.py source/bone-bottom.png out --map-id bone_bottom --zip

For publishing, upload `out/*-tiles.zip` to a GitHub Release and point each map's
`tiles.archive` in `pack.json` at the release URL.
