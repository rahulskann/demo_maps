# demo_maps

Map packs for [TOME](https://github.com/rahulskann/TOME), an offline interactive map app for
any game. One folder per game. These packs are separate from the TOME repo because they
contain third-party game art.

| Folder | Game | Add it in TOME |
| --- | --- | --- |
| [`silksong/`](silksong/) | Hollow Knight: Silksong | `rahulskann/demo_maps/silksong` |

To install one: open TOME → **Add pack** → paste the text from the last column.

---

## Make your own map

A pack is a folder with a `pack.json`, one or more map images cut into tiles, and marker
files. You'll need Python 3 and a copy of the TOME repo for its tools:

    git clone https://github.com/rahulskann/TOME.git
    cd TOME && python -m venv .venv && .venv/Scripts/pip install -r tools/slicer/requirements.txt

(On macOS/Linux use `.venv/bin/pip`.) The commands below assume TOME and your pack folder
sit side by side.

### 1. Make a folder and add your map image

    mygame/
    ├── source/world.png      the full-size map image
    ├── markers/              marker files, one per map
    └── pack.json

Use the largest, cleanest image you can: players zoom right in. Very large images
(8000+ px) are fine; they're cut into tiles. Only use art you're allowed to share, and
credit it in your README.

### 2. Cut the image into tiles

    python ../TOME/tools/slicer/slice_map.py source/world.png out --map-id world --zip

This writes `out/world-tiles.zip` and prints a `maps` entry to paste into `pack.json`.
Do this for each map (a world map, dungeon maps, region close-ups…). Keep `out/` out of
git; the zips go in a GitHub Release (step 6).

### 3. Write pack.json

```json
{
  "schemaVersion": 1,
  "id": "yourname.mygame",
  "name": "My Game Map",
  "game": "My Game",
  "author": "yourname",
  "version": "1.0.0",
  "description": "Every chest and secret in My Game.",
  "categoryGroups": [
    { "id": "loot", "name": "Loot" },
    { "id": "travel", "name": "Travel" }
  ],
  "categories": [
    { "id": "chest", "name": "Chests", "group": "loot", "color": "#E8B04A", "icon": "chest" },
    { "id": "save", "name": "Save Points", "group": "travel", "color": "#7FB2F0", "icon": "bench" }
  ],
  "maps": [ ...the entries the slicer printed... ]
}
```

- `id` must be unique and **never change** after publishing: players' progress is saved
  under it. Convention: `githubname.gamename`.
- Categories are yours to define per game, each with a colour and an icon. The icon
  names are listed in the
  [pack format](https://github.com/rahulskann/TOME/blob/main/docs/pack-format.md#category-icons).
- Bump `version` whenever you publish changes; that's how TOME knows to offer an update.

### 4. Add markers

Either edit `markers/world.json` by hand (positions are pixels on the full-size image,
measured from the top-left, so you can read them in any image editor):

```json
[
  { "id": "chest_cave_01", "name": "Cave Chest", "category": "chest", "x": 1420, "y": 842,
    "description": "Behind the waterfall. Needs the double jump." }
]
```

…or place them on your phone: open the map in TOME, tap the **pencil**, then
**long-press** to drop a marker. Marker `id`s must never change or be reused.

Optional extras:
- **Regions:** name the areas of a map so they show in its ⓘ info sheet and in search.
  Outline a region and point it at another map to make it open a detailed map.
- **Wiki links:** set `"wiki"` on the pack to a wiki's page URL prefix; categories and
  markers can then link pages by name. If you copy text from a wiki, check its licence
  (most are CC BY-SA: credit them via `source` and share your markers under CC BY-SA).
  `TOME/tools/wiki_text.py` fetches page text politely.

Full details: [pack format](https://github.com/rahulskann/TOME/blob/main/docs/pack-format.md).

### 5. Test it on your phone (optional)

With a debug build of TOME on an Android phone connected by USB:

    python ../TOME/tools/sideload_pack.py .            # copy the pack to the phone
    python ../TOME/tools/pull_markers.py .             # copy markers you placed back

### 6. Publish

Push your pack folder to a public GitHub repo, then attach the tile zips to a release:

    python ../TOME/tools/publish_pack.py . --repo yourname/yourrepo

That points `pack.json` at the release and prints the `gh release create …` command to
run. Commit and push `pack.json`, run that command, and anyone can add your pack in TOME
with `yourname/yourrepo/folder`.

To update later: edit, bump `version`, rebuild the zips if images changed, run
`publish_pack.py` again (it uses a new release tag per version), commit, push, and create
the release. Players get **Check for update** on the pack.
