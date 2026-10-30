"""Build the GPS Test pack: maps of real places, drawn from OpenStreetMap data and pinned
to the Earth so TOME can show "you are here".

Each map is drawn here from OpenMapTiles vector tiles served by OpenFreeMap (OpenStreetMap
data), cut into tiles with TOME's slicer, and pinned with nine points on a grid. From the
pack folder, with TOME's repo beside this one:

    python tools/build.py                     # every map, or name some: portland seattle
    python ../../TOME/tools/publish_pack.py . --repo rahulskann/demo_maps

Downloads are cached in out/cache (delete it to pick up newer map data) and keep to
OpenFreeMap's rules: one request at a time, a User-Agent naming this tool, and far fewer
than 3,000 tiles or 50 MB per map. Needs Pillow.
"""

import argparse
import json
import math
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None

PACK = Path(__file__).resolve().parent.parent
OUT = PACK / 'out'
CACHE = OUT / 'cache'
SLICER = PACK.parent.parent / 'TOME' / 'tools' / 'slicer' / 'slice_map.py'

UA = 'TOME GPS test pack builder (+https://github.com/rahulskann/demo_maps)'
TILEJSON = 'https://tiles.openfreemap.org/planet'
DATA_Z = 14             # OpenMapTiles' most detailed tiles
DRAW_Z = 15             # one image pixel is one web-map pixel at zoom 15 (about 3 m)
TILE_PX = 256 << (DRAW_Z - DATA_Z)  # image pixels per data tile
SS = 2                  # each tile is drawn at 2x, then halved, for smooth edges

CREDIT = '© OpenMapTiles © OpenStreetMap contributors'
SOURCE = {'name': 'OpenStreetMap contributors, drawn from OpenMapTiles via OpenFreeMap',
          'url': 'https://www.openstreetmap.org/copyright', 'license': 'ODbL'}
TEST_PHOTO = 'photos/test.jpg'

# bounds: (north, west, south, east). The map opens on its first marker, which also
# carries the test photo. Markers snap to the OpenStreetMap place of the same name (or
# the name given after the description) within 800 m, so they sit exactly on the map.
MAPS = [
    dict(id='portland', name='Portland and Bethany', bounds=(45.62, -122.90, 45.46, -122.55),
         about='Portland, Oregon, from Bethany and Forest Park in the west to I-205 in the east, '
               'and from St. Johns down to Sellwood.',
         markers=[
             ('pioneer-square', 'Pioneer Courthouse Square', 'landmark', 45.5189, -122.6793,
              "The square in the middle of downtown, known as Portland's living room."),
             ('powells', "Powell's City of Books", 'landmark', 45.5231, -122.6813,
              'A bookshop that fills a whole city block.'),
             ('omsi', 'Oregon Museum of Science and Industry', 'landmark', 45.5084, -122.6655,
              'Science museum on the east bank of the Willamette.'),
             ('pittock', 'Pittock Mansion', 'landmark', 45.5252, -122.7163,
              'A 1914 house high in the West Hills, now a museum.'),
             ('moda-center', 'Moda Center', 'landmark', 45.5316, -122.6668,
              'Arena, home of the Trail Blazers.'),
             ('rose-garden', 'International Rose Test Garden', 'park', 45.5193, -122.7058,
              'Rose garden in Washington Park, with views over the city.'),
             ('waterfront-park', 'Tom McCall Waterfront Park', 'park', 45.5155, -122.6717,
              'Riverside park along the west bank of the Willamette.', 'Governor Tom McCall Waterfront Park'),
             ('laurelhurst', 'Laurelhurst Park', 'park', 45.5212, -122.6253,
              'Park with a pond in Southeast Portland.'),
             ('mt-tabor', 'Mount Tabor Park', 'park', 45.5117, -122.5939,
              'Park on a volcanic cinder cone, with old reservoirs.'),
         ]),
    dict(id='seattle', name='Seattle', bounds=(47.735, -122.44, 47.495, -122.24),
         about='Seattle, Washington, from Northgate down to Rainier Beach, and from Discovery Park '
               'across to Lake Washington.',
         markers=[
             ('pike-place', 'Pike Place Market', 'landmark', 47.6097, -122.3422,
              'Public market above Elliott Bay, open since 1907.'),
             ('space-needle', 'Space Needle', 'landmark', 47.6205, -122.3493,
              'The tower built for the 1962 World\'s Fair.'),
             ('central-library', 'Seattle Central Library', 'landmark', 47.6067, -122.3325,
              'Glass-and-steel public library downtown, opened in 2004.',
              'The Seattle Public Library - Central Library'),
             ('lumen-field', 'Lumen Field', 'landmark', 47.5952, -122.3316,
              'Stadium of the Seahawks and the Sounders.'),
             ('suzzallo', 'Suzzallo Library', 'landmark', 47.6557, -122.3080,
              "The University of Washington's main library."),
             ('kerry-park', 'Kerry Park', 'park', 47.6295, -122.3599,
              'Small park on Queen Anne Hill with the classic view of downtown.'),
             ('gas-works', 'Gas Works Park', 'park', 47.6456, -122.3344,
              'Park built round an old gasworks on Lake Union.'),
             ('discovery-park', 'Discovery Park', 'park', 47.6573, -122.4055,
              "Seattle's largest park, on the bluffs of Magnolia."),
             ('green-lake', 'Green Lake Park', 'park', 47.6800, -122.3280,
              'A lake with a path about three miles round it.'),
         ]),
    dict(id='baltimore', name='Baltimore', bounds=(39.375, -76.72, 39.195, -76.52),
         about='Baltimore, Maryland: the whole city, from the Inner Harbor out to its edges.',
         markers=[
             ('aquarium', 'National Aquarium', 'landmark', 39.2851, -76.6084,
              'Aquarium on the Inner Harbor.'),
             ('fort-mchenry', 'Fort McHenry', 'landmark', 39.2633, -76.5799,
              'Star-shaped fort whose defence in 1814 inspired The Star-Spangled Banner.'),
             ('camden-yards', 'Oriole Park at Camden Yards', 'landmark', 39.2839, -76.6217,
              'Home of the Orioles, opened in 1992.'),
             ('mt-bank-stadium', 'M&T Bank Stadium', 'landmark', 39.2780, -76.6227,
              'Home of the Ravens.'),
             ('washington-monument', 'Washington Monument', 'landmark', 39.2975, -76.6156,
              'Column topped by George Washington, in Mount Vernon Place.'),
             ('federal-hill', 'Federal Hill Park', 'park', 39.2795, -76.6110,
              'Hilltop park looking over the Inner Harbor.'),
             ('patterson-park', 'Patterson Park', 'park', 39.2895, -76.5810,
              'East Baltimore park with a pagoda.'),
             ('druid-hill', 'Druid Hill Park', 'park', 39.3215, -76.6400,
              'Large park in the north-west of the city, home to the Maryland Zoo.'),
         ]),
    dict(id='corvallis', name='Corvallis', bounds=(44.62, -123.35, 44.52, -123.21),
         about='Corvallis, Oregon: Oregon State University, downtown and the Willamette, '
               'with Bald Hill to the west.',
         markers=[
             ('memorial-union', 'Memorial Union', 'landmark', 44.5649, -123.2789,
              "Oregon State University's student union, on the quad."),
             ('reser', 'Reser Stadium', 'landmark', 44.5596, -123.2814,
              "Oregon State's football stadium."),
             ('courthouse', 'Benton County Courthouse', 'landmark', 44.5646, -123.2617,
              'A courthouse from the late 1880s, still in use.'),
             ('riverfront', 'Riverfront Commemorative Park', 'park', 44.5653, -123.2585,
              'Downtown park along the Willamette.', 'Riverfront Commemorative City Park'),
             ('avery-park', 'Avery Park', 'park', 44.5547, -123.2730,
              'Park by the Marys River, with a rose garden.', 'Avery City Park'),
             ('chip-ross', 'Chip Ross Park', 'park', 44.6103, -123.2827,
              'Hilltop park with trails, north of town.'),
             ('bald-hill', 'Bald Hill Natural Area', 'park', 44.5726, -123.3330,
              'Hill with oak savanna and trails, west of town.'),
         ]),
]

CATEGORIES = [
    {'id': 'landmark', 'name': 'Landmarks', 'color': '#E0A030', 'icon': 'flag'},
    {'id': 'park', 'name': 'Parks', 'color': '#4C9A52', 'icon': 'flower'},
]

# ---- Web Mercator ------------------------------------------------------------------------


def to_world(lat, lng):
    n = 256 << DRAW_Z
    return ((lng + 180) / 360 * n,
            (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)


def to_latlng(x, y):
    n = 256 << DRAW_Z
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n)))), x / n * 360 - 180


def metres_per_px(lat):
    return 40075016.686 * math.cos(math.radians(lat)) / (256 << DRAW_Z)


class Frame:
    """A map's image: pixels at DRAW_Z, with the top-left at (x0, y0) in world pixels."""

    def __init__(self, bounds):
        north, west, south, east = bounds
        x0, y0 = to_world(north, west)
        x1, y1 = to_world(south, east)
        self.x0, self.y0 = math.floor(x0), math.floor(y0)
        self.w, self.h = math.ceil(x1) - self.x0, math.ceil(y1) - self.y0

    def px(self, lat, lng):
        x, y = to_world(lat, lng)
        return x - self.x0, y - self.y0

    def latlng(self, x, y):
        return to_latlng(x + self.x0, y + self.y0)

    def tiles(self):
        return [(tx, ty)
                for ty in range(self.y0 // TILE_PX, (self.y0 + self.h - 1) // TILE_PX + 1)
                for tx in range(self.x0 // TILE_PX, (self.x0 + self.w - 1) // TILE_PX + 1)]


# ---- Downloads -----------------------------------------------------------------------------

_tile_url = None


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as r:
                return r.read()
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def data_tile(tx, ty):
    global _tile_url
    path = CACHE / f'{DATA_Z}_{tx}_{ty}.pbf'
    if not path.exists():
        if _tile_url is None:
            _tile_url = json.loads(fetch(TILEJSON))['tiles'][0]
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fetch(_tile_url.format(z=DATA_Z, x=tx, y=ty)))
        time.sleep(0.1)
    return path.read_bytes()


# ---- Mapbox vector tiles (protobuf) ----------------------------------------------------------


def _varint(b, i):
    result = shift = 0
    while True:
        c = b[i]
        i += 1
        result |= (c & 0x7F) << shift
        if c < 0x80:
            return result, i
        shift += 7


def _fields(b):
    i, n = 0, len(b)
    while i < n:
        key, i = _varint(b, i)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, i = _varint(b, i)
        elif wire == 2:
            size, i = _varint(b, i)
            value, i = b[i:i + size], i + size
        elif wire == 1:
            value, i = b[i:i + 8], i + 8
        elif wire == 5:
            value, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f'unsupported wire type {wire}')
        yield field, value


def _packed(b):
    out, i = [], 0
    while i < len(b):
        v, i = _varint(b, i)
        out.append(v)
    return out


def _value(b):
    for field, v in _fields(b):
        if field == 1:
            return bytes(v).decode('utf-8')
        if field == 2:
            return struct.unpack('<f', v)[0]
        if field == 3:
            return struct.unpack('<d', v)[0]
        if field in (4, 5):
            return v
        if field == 6:
            return (v >> 1) ^ -(v & 1)
        if field == 7:
            return bool(v)
    return None


def _geometry(cmds):
    parts, x, y, i = [], 0, 0, 0
    while i < len(cmds):
        command, count = cmds[i] & 7, cmds[i] >> 3
        i += 1
        if command == 7:  # ClosePath
            if parts:
                parts[-1].append(parts[-1][0])
            continue
        for _ in range(count):
            a, b = cmds[i], cmds[i + 1]
            i += 2
            x += (a >> 1) ^ -(a & 1)
            y += (b >> 1) ^ -(b & 1)
            if command == 1:  # MoveTo
                parts.append([(x, y)])
            else:
                parts[-1].append((x, y))
    return parts


def decode(data):
    """{layer: [(type, props, parts)]}, parts in 0..1 of the tile (1 = 4096 units)."""
    layers = {}
    for field, layer in _fields(memoryview(data)):
        if field != 3:
            continue
        name, extent, keys, values, raw = '', 4096, [], [], []
        for f, v in _fields(layer):
            if f == 1:
                name = bytes(v).decode()
            elif f == 2:
                raw.append(v)
            elif f == 3:
                keys.append(bytes(v).decode())
            elif f == 4:
                values.append(_value(v))
            elif f == 5:
                extent = v
        features = []
        for fb in raw:
            gtype, tags, geom = 0, [], []
            for f, v in _fields(fb):
                if f == 2:
                    tags = _packed(v)
                elif f == 3:
                    gtype = v
                elif f == 4:
                    geom = _packed(v)
            props = {keys[tags[k]]: values[tags[k + 1]] for k in range(0, len(tags), 2)}
            parts = [[(x / extent, y / extent) for x, y in p] for p in _geometry(geom)]
            features.append((gtype, props, parts))
        layers[name] = features
    return layers


def signed_area(ring):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:]))


# ---- Style -----------------------------------------------------------------------------

LAND = '#F2EFE9'
WATER = '#A9D2E3'
WATER_TEXT = '#3F7398'
BUILDING, BUILDING_EDGE = '#DED7CE', '#CCC3B8'
LANDCOVER = {'wood': '#D2E5C3', 'forest': '#D2E5C3', 'grass': '#E2EDD1', 'farmland': '#EEF0D7',
             'wetland': '#D6E6DA', 'sand': '#F2E8C4', 'scrub': '#DCE8C9'}
LANDUSE = {'commercial': '#F3E9E7', 'retail': '#F3E5E3', 'industrial': '#ECE5EC', 'railway': '#EAE4E2',
           'cemetery': '#D5E3C6', 'hospital': '#F6E4E4', 'school': '#F4EDD2', 'university': '#F4EDD2',
           'college': '#F4EDD2', 'kindergarten': '#F4EDD2', 'stadium': '#D7EBD3', 'pitch': '#CFE7C9',
           'playground': '#D7EBD3', 'garages': '#ECE8E2'}
PARK = '#CDE6BE'
PARKS = {'park', 'garden', 'golf_course', 'recreation_ground', 'village_green', 'dog_park'}  # landcover subclasses
APRON, RUNWAY = '#E2DEE6', '#CBC7D2'

# class: (rank, width in image px, fill, casing)
ROADS = {
    'motorway': (10, 8.0, '#E892A2', '#C2566E'),
    'trunk': (9, 7.0, '#F9B29C', '#C47B62'),
    'primary': (8, 6.5, '#FCD6A4', '#B98C45'),
    'secondary': (7, 6.0, '#F7FABF', '#A6A863'),
    'tertiary': (6, 5.0, '#FFFFFF', '#B2ACA3'),
    'busway': (5, 4.0, '#FFFFFF', '#B2ACA3'),
    'minor': (5, 4.0, '#FFFFFF', '#C2BCB3'),
    'service': (3, 2.2, '#FFFFFF', '#C8C2B9'),
    'raceway': (3, 2.2, '#F1D3D8', None),
    'track': (2, 1.4, '#B89F7C', None),
    'path': (1, 1.2, '#E58A78', None),
}
RAILS = {'rail': (2.2, '#9C9C9C'), 'transit': (2.0, '#8C82B8')}
WATERWAYS = {'river': 3.0, 'canal': 3.0, 'stream': 1.4, 'ditch': 1.0, 'drain': 1.0}

_fonts = {}


def font(style, size):
    key = (style, size)
    if key not in _fonts:
        names = {'regular': ['arial.ttf', 'DejaVuSans.ttf'],
                 'bold': ['arialbd.ttf', 'DejaVuSans-Bold.ttf'],
                 'italic': ['ariali.ttf', 'DejaVuSans-Oblique.ttf']}[style]
        for name in names:
            try:
                _fonts[key] = ImageFont.truetype(name, size)
                break
            except OSError:
                continue
        else:
            _fonts[key] = ImageFont.load_default(size)
    return _fonts[key]


def lighten(colour, amount):
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return '#%02X%02X%02X' % tuple(round(c + (255 - c) * amount) for c in (r, g, b))


# ---- Drawing one data tile ------------------------------------------------------------------


def draw_tile(layers):
    size = TILE_PX * SS
    img = Image.new('RGB', (size, size), LAND)
    d = ImageDraw.Draw(img)

    def pts(part):
        return [(x * size, y * size) for x, y in part]

    def fill(features, colour, edge=None):
        if not features:
            return
        mask = Image.new('L', img.size, 0)
        m = ImageDraw.Draw(mask)
        for parts in features:
            for ring in parts:
                if len(ring) >= 3:
                    m.polygon(pts(ring), fill=255 if signed_area(ring) > 0 else 0)
        img.paste(colour, mask=mask)
        if edge:
            for parts in features:
                for ring in parts:
                    if len(ring) >= 3:
                        d.line(pts(ring), fill=edge, width=1)

    def stroke(parts, width, colour, caps=True):
        w = max(1, round(width * SS))
        for part in parts:
            if len(part) < 2:
                continue
            line = pts(part)
            d.line(line, fill=colour, width=w, joint='curve' if w > 2 else None)
            if caps and w > 3:
                r = w / 2 - 0.5
                for x, y in (line[0], line[-1]):
                    d.ellipse((x - r, y - r, x + r, y + r), fill=colour)

    def polygons(layer, test=lambda p: True):
        return [(p, parts) for t, p, parts in layers.get(layer, ()) if t == 3 and test(p)]

    for cls, colour in LANDCOVER.items():
        fill([parts for p, parts in polygons('landcover', lambda p: p.get('class') == cls
                                             and p.get('subclass') not in PARKS)], colour)
    for cls, colour in LANDUSE.items():
        fill([parts for p, parts in polygons('landuse', lambda p: p.get('class') == cls)], colour)
    fill([parts for p, parts in polygons('park')] +
         [parts for p, parts in polygons('landcover', lambda p: p.get('subclass') in PARKS)], PARK)
    fill([parts for p, parts in polygons('aeroway', lambda p: p.get('class') in ('aerodrome', 'apron'))], APRON)
    fill([parts for p, parts in polygons('aeroway', lambda p: p.get('class') in ('runway', 'taxiway'))], RUNWAY)
    for t, p, parts in layers.get('waterway', ()):
        if t == 2 and p.get('brunnel') != 'tunnel' and p.get('class') in WATERWAYS:
            stroke(parts, WATERWAYS[p['class']], WATER)
    fill([parts for p, parts in polygons('water', lambda p: p.get('brunnel') != 'tunnel')], WATER)
    for t, p, parts in layers.get('aeroway', ()):
        if t == 2:
            stroke(parts, 12 if p.get('class') == 'runway' else 3, RUNWAY, caps=False)
    fill([parts for p, parts in polygons('transportation', lambda p: p.get('class') == 'pier')], LAND)
    fill([parts for p, parts in polygons('building')], BUILDING, BUILDING_EDGE)

    roads = {'tunnel': [], 'ground': [], 'bridge': []}
    for t, p, parts in layers.get('transportation', ()):
        if t != 2:
            continue
        cls = p.get('class', '')
        level = p.get('brunnel') if p.get('brunnel') in ('tunnel', 'bridge') else 'ground'
        if cls in RAILS:
            if level != 'tunnel':
                roads[level].append((0, cls, p, parts))
        elif cls in ROADS:
            roads[level].append((ROADS[cls][0], cls, p, parts))
    for level in ('tunnel', 'ground', 'bridge'):
        items = sorted(roads[level], key=lambda r: r[0])
        for rank, cls, p, parts in items:  # casings, under every fill
            if cls in ROADS and ROADS[cls][3]:
                _, width, _, casing = ROADS[cls]
                width *= 0.6 if p.get('ramp') else 1
                if level == 'bridge':
                    casing = '#7E766B'
                elif level == 'tunnel':
                    casing = lighten(casing, 0.5)
                stroke(parts, width + 2, casing)
        for rank, cls, p, parts in items:
            if cls in RAILS:
                width, colour = RAILS[cls]
                stroke(parts, width, colour, caps=False)
                continue
            _, width, colour, _ = ROADS[cls]
            width *= 0.6 if p.get('ramp') else 1
            stroke(parts, width, lighten(colour, 0.45) if level == 'tunnel' else colour)
    return img.reduce(SS)


# ---- Labels ---------------------------------------------------------------------------------

ABBREVIATIONS = [
    (r'^Northwest ', 'NW '), (r'^Northeast ', 'NE '), (r'^Southwest ', 'SW '), (r'^Southeast ', 'SE '),
    (r'^North ', 'N '), (r'^South ', 'S '), (r'^East ', 'E '), (r'^West ', 'W '),
    (r' Street$', ' St'), (r' Avenue$', ' Ave'), (r' Boulevard$', ' Blvd'), (r' Road$', ' Rd'),
    (r' Drive$', ' Dr'), (r' Highway$', ' Hwy'), (r' Parkway$', ' Pkwy'), (r' Place$', ' Pl'),
    (r' Court$', ' Ct'), (r' Lane$', ' Ln'), (r' Terrace$', ' Ter'),
    (r' Street (North|South|East|West|Northwest|Northeast|Southwest|Southeast)$', r' St \1'),
    (r' Avenue (North|South|East|West|Northwest|Northeast|Southwest|Southeast)$', r' Ave \1'),
]
DIRECTIONS = {'North': 'N', 'South': 'S', 'East': 'E', 'West': 'W', 'Northwest': 'NW',
              'Northeast': 'NE', 'Southwest': 'SW', 'Southeast': 'SE'}


def drawable(text):
    """Drops emoji and other symbols the map fonts don't have."""
    return re.sub(r'\s+', ' ', ''.join(c for c in text if ord(c) < 0x2000 or c in '‐–—‘’“”…')).strip()


def street(name):
    for pattern, short in ABBREVIATIONS:
        name = re.sub(pattern, short, name)
    return re.sub(r' (St|Ave) (North|South|East|West|Northwest|Northeast|Southwest|Southeast)$',
                  lambda m: f' {m[1]} {DIRECTIONS[m[2]]}', name)


# (font style, size, colour, uppercase, min distance between repeats)
PLACE_LABELS = {
    'city': ('bold', 24, '#2B2B2B', False), 'town': ('bold', 20, '#2B2B2B', False),
    'village': ('bold', 16, '#333333', False), 'suburb': ('bold', 14, '#5A5550', True),
    'quarter': ('bold', 12, '#6A645E', True), 'neighbourhood': ('bold', 11, '#6F6962', True),
    'hamlet': ('regular', 12, '#555555', False), 'locality': ('regular', 11, '#666666', False),
    'island': ('italic', 13, '#555555', False),
}
ROAD_LABEL_CLASSES = {'motorway': 13, 'trunk': 13, 'primary': 13, 'secondary': 12, 'tertiary': 12,
                      'minor': 11, 'busway': 11}


class Labels:
    """Places text on the finished image without overlaps."""

    CELL = 64

    def __init__(self, img):
        self.img = img
        self.boxes = {}
        self.placed = {}

    def _cells(self, box):
        x0, y0, x1, y1 = box
        for cx in range(int(x0) // self.CELL, int(x1) // self.CELL + 1):
            for cy in range(int(y0) // self.CELL, int(y1) // self.CELL + 1):
                yield cx, cy

    def _free(self, boxes):
        for box in boxes:
            for cell in self._cells(box):
                for other in self.boxes.get(cell, ()):
                    if box[0] < other[2] and other[0] < box[2] and box[1] < other[3] and other[1] < box[3]:
                        return False
        return True

    def _near_same(self, name, x, y, distance):
        return any(math.hypot(x - px, y - py) < distance for px, py in self.placed.get(name, ()))

    def add(self, text, x, y, style, size, colour, angle=0.0, halo=2, repeat=200, key=None, within=None):
        """Draws text centred on (x, y), turned by angle degrees; False if there's no room.
        With within (a colour), only where the whole label sits on that colour."""
        text = drawable(text)
        key = key or text
        if not text or self._near_same(key, x, y, repeat):
            return False
        f = font(style, size)
        left, top, right, bottom = f.getbbox(text, stroke_width=halo)
        w, h = right - left, bottom - top
        a = math.radians(angle)
        ux, uy = math.cos(a), math.sin(a)
        # Boxes along the text's axis, so slanted labels don't block a whole square.
        n = max(1, math.ceil(w / h))
        boxes = []
        for i in range(n):
            t = (i + 0.5) / n * w - w / 2
            cx, cy = x + ux * t, y + uy * t
            r = max(h, w / n) / 2 + 2
            boxes.append((cx - r, cy - h / 2 - 2, cx + r, cy + h / 2 + 2) if angle == 0 else
                         (cx - h / 2 - 2, cy - h / 2 - 2, cx + h / 2 + 2, cy + h / 2 + 2))
        if any(b[0] < 2 or b[1] < 2 or b[2] > self.img.width - 2 or b[3] > self.img.height - 2 for b in boxes):
            return False
        if not self._free(boxes):
            return False
        if within and any(self.img.getpixel((round(b[0]), round(b[1]))) != within or
                          self.img.getpixel((round(b[2]), round(b[3]))) != within for b in boxes):
            return False
        label = Image.new('RGBA', (w + 4, h + 4), (0, 0, 0, 0))
        ImageDraw.Draw(label).text((2 - left, 2 - top), text, font=f, fill=colour,
                                   stroke_width=halo, stroke_fill=(255, 255, 255, 235))
        if angle:
            label = label.rotate(-angle, expand=True, resample=Image.Resampling.BICUBIC)
        self.img.paste(label, (round(x - label.width / 2), round(y - label.height / 2)), label)
        for box in boxes:
            for cell in self._cells(box):
                self.boxes.setdefault(cell, []).append(box)
        self.placed.setdefault(key, []).append((x, y))
        return True

    def along(self, text, line, style, size, colour, repeat=450):
        """Puts text on the straightest stretch of a line long enough for it."""
        text = drawable(text)
        f = font(style, size)
        need = f.getlength(text) + 12
        cum = [0.0]
        for a, b in zip(line, line[1:]):
            cum.append(cum[-1] + math.dist(a, b))
        total = cum[-1]
        if total < need:
            return False

        def at(s):
            i = max(1, min(len(cum) - 1, next((k for k in range(1, len(cum)) if cum[k] >= s), len(cum) - 1)))
            (x0, y0), (x1, y1) = line[i - 1], line[i]
            t = 0 if cum[i] == cum[i - 1] else (s - cum[i - 1]) / (cum[i] - cum[i - 1])
            return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t

        middle = (total - need) / 2
        starts = sorted((s * 10.0 for s in range(int((total - need) / 10) + 1)), key=lambda s: abs(s - middle))
        for s in starts[:12]:
            (x0, y0), (x1, y1) = at(s), at(s + need)
            if math.dist((x0, y0), (x1, y1)) < need * 0.97:
                continue
            angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
            if angle > 90:
                angle -= 180
            elif angle <= -90:
                angle += 180
            if self.add(text, (x0 + x1) / 2, (y0 + y1) / 2, style, size, colour, angle, repeat=repeat):
                return True
        return False


# ---- Building one map --------------------------------------------------------------------


def build_map(spec):
    frame = Frame(spec['bounds'])
    tiles = frame.tiles()
    print(f"{spec['id']}: {frame.w}x{frame.h} px, {len(tiles)} data tiles")
    img = Image.new('RGB', (frame.w, frame.h), LAND)
    places, pois, reserves, peaks, waters, roads, rivers = [], [], [], [], [], [], []
    for n, (tx, ty) in enumerate(tiles, 1):
        layers = decode(data_tile(tx, ty))
        ox, oy = tx * TILE_PX - frame.x0, ty * TILE_PX - frame.y0
        img.paste(draw_tile(layers), (ox, oy))

        def to_img(part):
            return [(ox + x * TILE_PX, oy + y * TILE_PX) for x, y in part]

        def inside(x, y):  # this tile's own area, not its buffer, so each point is kept once
            return ox <= x < ox + TILE_PX and oy <= y < oy + TILE_PX

        for t, p, parts in layers.get('place', ()):
            for x, y in (to_img(part)[0] for part in parts):
                if p.get('name') and inside(x, y):
                    places.append((p.get('class'), p['name'], x, y, p.get('rank', 99)))
        for t, p, parts in layers.get('poi', ()):
            for x, y in (to_img(part)[0] for part in parts):
                if p.get('name') and inside(x, y):
                    pois.append((p.get('class'), p['name'], x, y, p.get('rank', 99)))
        for t, p, parts in layers.get('park', ()):  # big parks' label points, for snapping markers
            for x, y in (to_img(part)[0] for part in parts):
                if t == 1 and p.get('name') and inside(x, y):
                    reserves.append((p['name'], x, y))
        for t, p, parts in layers.get('mountain_peak', ()):
            for x, y in (to_img(part)[0] for part in parts):
                if p.get('name') and inside(x, y) and p.get('class', 'peak') == 'peak':
                    peaks.append((p['name'], x, y, p.get('rank', 99)))
        for t, p, parts in layers.get('water_name', ()):
            if p.get('name'):
                for part in parts:
                    if t == 1 and inside(*to_img(part)[0]):
                        waters.append((p['name'], to_img(part)[0], p.get('class')))
                    elif t == 2:
                        rivers.append((p['name'], to_img(part)))
        for t, p, parts in layers.get('waterway', ()):
            if t == 2 and p.get('name') and p.get('class') in ('river', 'canal'):
                rivers.extend((p['name'], to_img(part)) for part in parts)
        for t, p, parts in layers.get('transportation_name', ()):
            cls = p.get('class')
            if t == 2 and cls in ROAD_LABEL_CLASSES:
                text = p.get('ref') if cls in ('motorway', 'trunk') and p.get('ref') else p.get('name')
                if text:
                    roads.extend((ROAD_LABEL_CLASSES[cls], cls, text, to_img(part)) for part in parts)
        if n % 20 == 0 or n == len(tiles):
            print(f'  drawn {n}/{len(tiles)}')

    labels = Labels(img)
    for cls in ('city', 'town', 'village', 'suburb'):
        for _, name, x, y, _ in sorted((p for p in places if p[0] == cls), key=lambda p: p[4]):
            style, size, colour, upper = PLACE_LABELS[cls]
            labels.add(name.upper() if upper else name, x, y, style, size, colour, halo=3)
    water = Image.new('RGB', (1, 1), WATER).getpixel((0, 0))
    for name, (x, y), cls in waters:  # only water big enough to hold its name, not fountains
        labels.add(name, x, y, 'italic', 15 if cls in ('sea', 'bay', 'lake') else 13, WATER_TEXT, within=water)
    for name, line in sorted(rivers, key=lambda r: -len(r[1])):
        labels.along(name, line, 'italic', 13, WATER_TEXT, repeat=700)
    major = [r for r in roads if r[1] in ('motorway', 'trunk', 'primary', 'secondary')]
    for size, cls, text, line in sorted(major, key=lambda r: -ROADS[r[1]][0]):
        labels.along(text if cls in ('motorway', 'trunk') else street(text), line, 'regular', size, '#333333')
    for cls in ('quarter', 'neighbourhood'):
        for _, name, x, y, _ in sorted((p for p in places if p[0] == cls), key=lambda p: p[4]):
            style, size, colour, upper = PLACE_LABELS[cls]
            labels.add(name.upper(), x, y, style, size, colour, halo=2)
    for name, x, y, _ in sorted(peaks, key=lambda p: p[3]):
        if labels.add(name, x, y + 12, 'regular', 11, '#6B4F3A'):
            ImageDraw.Draw(img).polygon([(x, y - 5), (x - 5, y + 3), (x + 5, y + 3)], fill='#8A6A4E')
    for _, name, x, y, _ in sorted((p for p in pois if p[0] == 'park'), key=lambda p: p[4]):
        labels.add(name, x, y, 'italic', 12, '#3E7A3E')
    minor = [r for r in roads if r[1] not in ('motorway', 'trunk', 'primary', 'secondary')]
    for size, cls, text, line in sorted(minor, key=lambda r: -ROADS[r[1]][0]):
        labels.along(street(text), line, 'regular', size, '#444444', repeat=350)
    for cls in ('hamlet', 'locality', 'island'):
        for _, name, x, y, _ in (p for p in places if p[0] == cls):
            style, size, colour, upper = PLACE_LABELS[cls]
            labels.add(name, x, y, style, size, colour)

    f = font('regular', 13)
    w = f.getlength(CREDIT)
    d = ImageDraw.Draw(img)
    d.rectangle((frame.w - w - 16, frame.h - 24, frame.w, frame.h), fill='#FFFFFF')
    d.text((frame.w - w - 8, frame.h - 20), CREDIT, font=f, fill='#333333')
    OUT.mkdir(exist_ok=True)
    img.save(OUT / f"{spec['id']}.png", compress_level=6)

    regions, seen = [], set()
    for cls, name, x, y, _ in places:
        if cls in ('city', 'town', 'village', 'suburb', 'quarter', 'neighbourhood', 'hamlet') \
                and 0 <= x < frame.w and 0 <= y < frame.h and name not in seen:
            seen.add(name)
            regions.append({'id': slug(name), 'name': name, 'x': round(x), 'y': round(y)})
    regions.sort(key=lambda r: r['name'])
    ids = set()
    for r in regions:
        while r['id'] in ids:
            r['id'] += '-2'
        ids.add(r['id'])

    named = {}
    for _, name, x, y, _ in pois:
        named.setdefault(name.lower(), []).append((x, y))
    for name, x, y, *_ in peaks + reserves:
        named.setdefault(name.lower(), []).append((x, y))
    markers = []
    for i, (mid, name, cat, lat, lng, text, *match) in enumerate(spec['markers']):
        x, y = frame.px(lat, lng)
        limit = 800 / metres_per_px(lat)
        near = [(math.dist((x, y), q), q) for q in named.get((match or [name])[0].lower(), ())]
        near = [n for n in near if n[0] < limit]
        if near:
            x, y = min(near)[1]
        else:
            print(f'  {name}: not found in the map data, placed from its coordinates')
        if not (0 <= x < frame.w and 0 <= y < frame.h):
            raise SystemExit(f'{name} is outside the {spec["id"]} map')
        marker = {'id': mid, 'name': name, 'category': cat, 'x': round(x), 'y': round(y),
                  'description': text + (' The photo is a test image.' if i == 0 else '')}
        if i == 0:
            marker['photo'] = TEST_PHOTO
        markers.append(marker)

    geo = []
    for fy in (0, 0.5, 1):
        for fx in (0, 0.5, 1):
            x, y = round(frame.w * fx), round(frame.h * fy)
            lat, lng = frame.latlng(x, y)
            geo.append([x, y, round(lat, 7), round(lng, 7)])
    max_zoom = max(0, math.ceil(math.log2(max(frame.w, frame.h) / 256)))
    entry = {
        'id': spec['id'], 'name': spec['name'],
        'image': {'width': frame.w, 'height': frame.h},
        'tileSize': 256, 'minZoom': 0, 'maxZoom': max_zoom,
        'tiles': {'archive': f"out/{spec['id']}-tiles.zip", 'path': '{z}/{x}/{y}.png'},
        'markers': f"markers/{spec['id']}.json",
        'initialView': {'x': markers[0]['x'], 'y': markers[0]['y'], 'zoom': max_zoom - 2},
        'description': spec['about'] + ' Drawn from OpenStreetMap data.',
        'source': SOURCE,
        'geo': {'points': geo},
        'regions': regions,
    }
    write_json(PACK / 'markers' / f"{spec['id']}.json", markers)
    print(f'  {len(markers)} markers, {len(regions)} places')
    return entry


def slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'place'


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def test_photo():
    path = PACK / TEST_PHOTO
    if path.exists():
        return
    photo = Image.new('RGB', (1200, 800))
    d = ImageDraw.Draw(photo)
    for y in range(800):
        t = y / 800
        d.line([(0, y), (1200, y)], fill=(int(90 + 120 * t), int(150 + 60 * t), int(230 - 80 * t)))
    d.ellipse([450, 260, 750, 560], fill=(240, 240, 250))
    d.text((80, 680), 'Test photo', fill=(20, 30, 40), font=font('bold', 64))
    path.parent.mkdir(exist_ok=True)
    photo.save(path, quality=85)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('maps', nargs='*', help='Map ids to rebuild (default: all)')
    parser.add_argument('--no-slice', action='store_true', help="Draw the images but don't cut tiles")
    args = parser.parse_args()
    unknown = set(args.maps) - {m['id'] for m in MAPS}
    if unknown:
        raise SystemExit(f'Unknown maps: {", ".join(sorted(unknown))}')

    manifest_path = PACK / 'pack.json'
    old = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    old_maps = {m['id']: m for m in old.get('maps', [])}
    test_photo()
    maps = []
    for spec in MAPS:
        if args.maps and spec['id'] not in args.maps:
            if spec['id'] in old_maps:
                maps.append(old_maps[spec['id']])
            continue
        entry = build_map(spec)
        if spec['id'] in old_maps and '://' in old_maps[spec['id']]['tiles']['archive']:
            entry['tiles'] = old_maps[spec['id']]['tiles']  # keep the published link
        maps.append(entry)
        if not args.no_slice:
            if not SLICER.exists():
                raise SystemExit(f'TOME slicer not found at {SLICER}')
            subprocess.run([sys.executable, str(SLICER), str(OUT / f"{spec['id']}.png"), str(OUT),
                            '--map-id', spec['id']], check=True, stdout=subprocess.DEVNULL)
            # Flat colours: a 256-colour palette per tile, like OpenStreetMap's own tiles,
            # makes the zips about 3x smaller and looks the same.
            tiles_dir = OUT / f"{spec['id']}-tiles"
            for tile in tiles_dir.rglob('*.png'):
                Image.open(tile).convert('RGBA').quantize(
                    256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(tile, optimize=True)
            shutil.make_archive(str(tiles_dir), 'zip', tiles_dir)
            print(f"  {spec['id']}-tiles.zip: {(OUT / f'{tiles_dir.name}.zip').stat().st_size / 1e6:.1f} MB")

    write_json(manifest_path, {
        'schemaVersion': 1,
        'id': 'rahulskann.gps-test',
        'name': 'GPS Test',
        'game': 'Real places',
        'author': 'rahulskann',
        'version': old.get('version', '1.0.0'),
        'description': 'Maps of Portland and Bethany, Seattle, Baltimore and Corvallis, pinned to the Earth. '
                       'Open one and tap the location button to see where you are, or how far away. '
                       'Map data © OpenStreetMap contributors.',
        'categories': CATEGORIES,
        'maps': maps,
    })
    print('Wrote pack.json. Bump "version" before publishing a change.')


if __name__ == '__main__':
    main()
