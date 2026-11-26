# -*- coding: utf-8 -*-
"""Build local ENU plan from OSM aeroway data + render a plan PNG.

Origin = ARP (25.929254, 119.672524) from OurAirports, or given.
Outputs: osm_plan.json (features in metres, x=east, y=north), osm_plan.png
"""
import json, math, os
from PIL import Image, ImageDraw, ImageFont

P = r"F:\dshproj\foc-t2\ref\zsfz_osm.json"
OUT = r"F:\dshproj\foc-t2\ref\derived"
os.makedirs(OUT, exist_ok=True)
ORIGIN = (25.929254, 119.672524)  # ARP

R = 6378137.0
def enu(lat, lon, lat0=ORIGIN[0], lon0=ORIGIN[1]):
    x = math.radians(lon - lon0) * R * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * R
    return x, y

def width_of(t, default):
    for k in ('width',):
        v = t.get(k)
        if v:
            try:
                return float(str(v).replace('m', '').strip())
            except Exception:
                pass
    return default

d = json.load(open(P, encoding='utf-8'))
feats = []
for e in d['elements']:
    if e['type'] != 'way':
        continue
    t = e['tags']
    aw = t.get('aeroway') or t.get('building')
    geom = [enu(p['lat'], p['lon']) for p in e['geometry']]
    feats.append({'id': e['id'], 'kind': aw, 'ref': t.get('ref'), 'name': t.get('name'),
                  'width': width_of(t, None), 'surface': t.get('surface'), 'pts': geom})

json.dump({'origin': ORIGIN, 'features': feats}, open(os.path.join(OUT, 'osm_plan.json'), 'w', encoding='utf-8'), ensure_ascii=False)

xs = [p[0] for f in feats for p in f['pts']]
ys = [p[1] for f in feats for p in f['pts']]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
print('extent m', round(minx), round(maxx), round(miny), round(maxy))

# render
S = 0.25  # m per px
W = int((maxx - minx) * S) + 80
H = int((maxy - miny) * S) + 80
def to_px(p):
    return (40 + (p[0] - minx) * S, H - 40 - (p[1] - miny) * S)

img = Image.new('RGB', (W, H), (30, 30, 34))
dr = ImageDraw.Draw(img)
order = {'apron': 0, 'runway': 1, 'taxiway': 2, 'terminal': 3, 'transportation': 3}
for f in sorted(feats, key=lambda f: order.get(f['kind'], 1)):
    pts = [to_px(p) for p in f['pts']]
    if f['kind'] in ('terminal', 'transportation'):
        dr.polygon(pts, fill=(240, 200, 80), outline=(255, 255, 255))
    elif f['kind'] == 'apron':
        dr.polygon(pts, fill=(60, 60, 70), outline=(90, 90, 100))
    elif f['kind'] == 'runway':
        dr.line(pts + [pts[0]] if len(pts) > 2 else pts, fill=(200, 200, 200), width=max(2, int(45 * S)))
    elif f['kind'] == 'taxiway':
        w = f['width'] or 0
        lw = max(2, int((w if w > 5 else 23) * S))
        dr.line(pts, fill=(120, 170, 220), width=lw)
img.save(os.path.join(OUT, 'osm_plan.png'))
print('png', img.size, os.path.join(OUT, 'osm_plan.png'))
