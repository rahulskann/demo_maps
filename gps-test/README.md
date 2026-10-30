# GPS Test: real places for TOME

Four city maps pinned to the Earth, for trying [TOME](https://github.com/rahulskann/TOME)'s
**you are here** button.

**Add it in TOME:** Add pack → `rahulskann/demo_maps/gps-test`

Open a map and tap the location button (top right). If you're on the map, you get a blue dot.
Anywhere else, an arrow at the edge of the screen says how far away you are and which way.
Your location stays on your phone: TOME only uses it while the map is open, after you turn it
on. The first marker on each map has a test photo, for trying marker photos.

## Maps

| Map | Covers | Size |
| --- | --- | --- |
| Portland and Bethany | Bethany and Forest Park to I-205, St. Johns to Sellwood | 27 × 18 km |
| Seattle | Northgate to Rainier Beach, Discovery Park to Lake Washington | 15 × 27 km |
| Baltimore | The whole city | 17 × 20 km |
| Corvallis | Oregon State, downtown and the Willamette, Bald Hill | 11 × 11 km |

Neighbourhood names are listed in each map's ⓘ info sheet and found by search. Markers are
a few well-known landmarks and parks.

## How the maps are made

`tools/build.py` draws each map from OpenStreetMap data (vector tiles in the OpenMapTiles
schema, from OpenFreeMap), then cuts it into tiles with TOME's slicer. The maps aren't
copies of openstreetmap.org's map images, because those can't be used offline.

Each map is pinned with nine points on a grid (`geo` in `pack.json`). The images use the
same projection as web maps, and over a city that's close enough to flat that the dot is
within 10 m of where the map says it is at the far corners of Seattle, and within a few
metres everywhere else. Phone GPS is usually no better than that.

## Rebuilding

Needs Python 3 with Pillow, and TOME's repo next to this one (for the slicer):

    python tools/build.py              # every map
    python tools/build.py seattle      # just one

Downloads are cached in `out/cache` (not committed); delete it to pick up newer
OpenStreetMap data. To add a city, add an entry to `MAPS` in `tools/build.py`: its bounds
and a few landmarks. The script prints how many data tiles each map needs; keep it in the
hundreds (OpenFreeMap allows up to 3,000 tiles or 50 MB per download).

Then bump `version` in `pack.json` and publish (see the [main README](../README.md#6-publish)):

    python ../../TOME/tools/publish_pack.py . --repo rahulskann/demo_maps

## Credits and licences

- **Map data** © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
  available under the [Open Database License](https://opendatacommons.org/licenses/odbl/).
  The map images are drawn from it, and marker positions are taken from it.
- **Vector tiles** © [OpenMapTiles](https://openmaptiles.org), served by
  [OpenFreeMap](https://openfreemap.org).
- **Marker notes** are licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- **`tools/build.py`** is MIT licensed, like TOME.
