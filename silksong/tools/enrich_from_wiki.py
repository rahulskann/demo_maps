"""Fill Silksong Atlas notes from the Hollow Knight Wiki (CC BY-SA 3.0), with credit.

- Categories with a `wiki` page get a general description ("About Benches").
- Maps with a `wiki` page get its introduction as their description.
- Regions and areas (each map's `regions`) get the area's description plus a
  "What's here" summary of items, NPCs and bosses.

Only fills text that is empty or was previously filled from the wiki (its
`source` names the wiki), so notes written by hand are never overwritten.
Re-run any time to pick up wiki edits; responses are cached in
tome/tools/.wiki-cache.

Usage (from demo_maps/silksong):
    python tools/enrich_from_wiki.py
"""

import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACK.parents[1] / "tome" / "tools"))

from wiki_text import area_features, page_wikitext, paragraphs, sections, to_plain  # noqa: E402

API = "https://hollowknight.wiki/mw/api.php"
WIKI_NAME = "Hollow Knight Wiki"
LICENSE = "CC BY-SA 3.0"
GAME = "Silksong"  # picks the right page when a name is shared with Hollow Knight
MAX_ABOUT = 1500  # characters of category text to keep offline

# Areas that are sections of another page rather than pages of their own.
SUB_AREAS = {
    "Mosshome": ("Bone Bottom", "Sub-area: Mosshome"),
    "Bonegrave": ("Bone Bottom", "Sub-area: Bonegrave"),
}


def source(title: str, base_url: str, section: str = "") -> dict:
    anchor = "#" + section.replace(" ", "_") if section else ""
    return {
        "name": f"{WIKI_NAME}: {title}" + (f" ({section.removeprefix('Sub-area: ')})" if section else ""),
        "url": base_url + title.replace(" ", "_") + anchor,
        "license": LICENSE,
    }


def ours_to_fill(entry: dict) -> bool:
    """Empty, or previously filled from the wiki (never hand-written text)."""
    if not entry.get("description"):
        return True
    return WIKI_NAME in (entry.get("source") or {}).get("name", "")


def summary(features: dict[str, list[str]]) -> str:
    lines = []
    for kind in ("Items", "NPCs", "Bosses"):
        if kind in features:
            lines.append(f"{kind}: " + "; ".join(features[kind]))
    return "\n".join(lines)


def area_text(page: str, section: str | None) -> tuple[str, str, str]:
    """(title, description, section used) for an area page or sub-area section."""
    title, wikitext = page_wikitext(API, page, prefer=GAME)
    secs = sections(wikitext)
    if section:
        raw = secs.get(section, "")
        prose = paragraphs(to_plain(raw))
        features = area_features(raw)
    else:
        raw = secs.get("Description") or secs.get("", "")
        prose = paragraphs(to_plain(raw))
        # The main area's feature list sits in its first non-sub-area section.
        features = next(
            (f for name, body in secs.items()
             if not name.startswith("Sub-area") and (f := area_features(body))),
            {},
        )
    parts = prose[:1]
    if features:
        parts.append("What's here\n" + summary(features))
    return title, "\n\n".join(parts), section or ""


def main() -> None:
    pack_path = PACK / "pack.json"
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    base_url = pack["wiki"]
    changed = 0

    for cat in pack.get("categories", []):
        if not cat.get("wiki") or not ours_to_fill(cat):
            continue
        title, wikitext = page_wikitext(API, cat["wiki"], prefer=GAME)
        about = "\n\n".join(paragraphs(to_plain(sections(wikitext)[""]), bullets=True))
        if len(about) > MAX_ABOUT:
            about = about[:MAX_ABOUT].rsplit("\n", 1)[0] + "\n…"
        if about:
            cat["description"] = about
            cat["source"] = source(title, base_url)
            changed += 1
            print(f"category {cat['id']}: {len(about)} chars from {title}")

    for m in pack["maps"]:
        if m.get("wiki") and ours_to_fill(m):
            title, wikitext = page_wikitext(API, m["wiki"], prefer=GAME)
            lead = paragraphs(to_plain(sections(wikitext)[""]))
            if lead:
                m["description"] = lead[0]
                m["source"] = source(title, base_url)
                changed += 1
                print(f"map {m['id']}: {len(lead[0])} chars from {title}")

        for region in m.get("regions", []):
            if not ours_to_fill(region):
                continue
            page, section = SUB_AREAS.get(region["name"], (region.get("wiki") or region["name"], None))
            try:
                title, text, used = area_text(page, section)
            except RuntimeError as e:
                print(f"  skipped {region['id']}: {e}")
                continue
            if not text:
                print(f"  no text for {region['id']}")
                continue
            region["description"] = text
            region["source"] = source(title, base_url, used)
            if not section and region.get("wiki") and region["wiki"] != title:
                print(f"  {region['id']}: wiki link {region['wiki']!r} -> {title!r}")
                region["wiki"] = title  # e.g. a disambiguation page resolved to the Silksong one
            changed += 1
            print(f"{m['id']}/{region['id']}: {len(text)} chars from {title} {used}".rstrip())

    pack_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    print(f"\n{changed} entries filled. Review with git diff before committing.")


if __name__ == "__main__":
    main()
