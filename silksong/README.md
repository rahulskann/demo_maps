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
- **Marker data** (`markers/*.json` and the category notes in `pack.json`: names,
  positions, descriptions) is licensed
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- **Region, area and category descriptions** are adapted from the
  [Hollow Knight Wiki](https://hollowknight.wiki), licensed
  [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Each adapted entry
  names and links its source page in its `source` field, and the app shows that credit
  under the text. Changes: trimmed to the first paragraph, markup removed, and the
  page's item/NPC/boss lists summarised under "What's here".

## Refreshing wiki text

    python tools/enrich_from_wiki.py

Fills empty notes and refreshes ones previously taken from the wiki; notes written by hand
are left alone. Review with `git diff`.

## Building

Tiles are built from `source/` with TOME's slicer and are not committed:

    python ../../tome/tools/slicer/slice_map.py source/world.png out --map-id world --zip
    python ../../tome/tools/slicer/slice_map.py source/bone-bottom.png out --map-id bone_bottom --zip

For publishing, upload `out/*-tiles.zip` to a GitHub Release and point each map's
`tiles.archive` in `pack.json` at the release URL.
