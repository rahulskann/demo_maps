# Silksong Atlas: a TOME map pack

An unofficial, fan-made map pack for **Hollow Knight: Silksong**, for the
[TOME](https://github.com/rahulskann/TOME) offline map app.

**Add it in TOME:** Add pack → `rahulskann/demo_maps/silksong`

> Not affiliated with or endorsed by Team Cherry. This pack is free and always will be.
> If you represent Team Cherry and would like it changed or removed, open an issue and
> it will be taken down promptly.

## Maps

| Map | Image | Notes |
| --- | --- | --- |
| Pharloom | `source/Silksong_start.png` | Region overview. Zoom in anywhere to continue on the detailed map; all 22 regions are listed in the ⓘ info sheet. |
| Pharloom (detailed) | `source/Silksong_end.png` | The whole world in detail, from regions down to rooms, with all markers. Zoom out to return to the overview. |

`source/moss-grotto.png` and `source/the-marrow.png` are earlier region close-ups, kept for
reference; marker positions measured on them were converted onto the detailed map.

Marker types: benches, Bellways, Mask Shards, Spool Fragments, Crests, Tools, Craftmetal,
Memory Lockets, Lost Fleas. Many are still empty; add them in TOME's edit mode and send a
pull request.

## Credits and licences

- **Map art** is from *Hollow Knight: Silksong*, © Team Cherry. The higher-quality map
  images were shared by the **Reddit community**. Neither is covered by the licence below.
- **Marker data** (`markers/*.json` and the notes in `pack.json`: names, positions,
  descriptions) is licensed
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- **Region, area, map and category descriptions** are adapted from the
  [Hollow Knight Wiki](https://hollowknight.wiki), licensed
  [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). Each adapted entry
  names and links its source page in its `source` field, and the app shows that credit
  under the text. Changes: trimmed to the first paragraph, markup removed, and the
  page's item/NPC/boss lists summarised under "What's here".

## Refreshing wiki text

    python tools/enrich_from_wiki.py

Fills empty notes and refreshes ones previously taken from the wiki; notes written by hand
are left alone. Review with `git diff`.

## Building and publishing

Tiles are built from `source/` with TOME's slicer into `out/` (not committed):

    python ../../TOME/tools/slicer/slice_map.py source/Silksong_start.png out --map-id world --zip
    python ../../TOME/tools/slicer/slice_map.py source/Silksong_end.png out --map-id pharloom_detailed --zip

Then publish (see the [main README](../README.md#6-publish)):

    python ../../TOME/tools/publish_pack.py . --repo rahulskann/demo_maps
