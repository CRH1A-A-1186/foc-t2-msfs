# -*- coding: utf-8 -*-
"""Overlay: chart buildings/pavement (ENU) vs OSM aeroway (ENU)."""
import json, os, math
from PIL import Image, ImageDraw

REF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ch = json.load(open(os.path.join(REF, 'ref', 'derived', 'chart_enu.json'), encoding='utf-8'))
osm = json.load(open(os.path.join(REF, 'ref', 'derived', 'osm_plan.json'), encoding='utf-8'))
f = ch['features']
pts = [p for k in f for ln in f[k] for p in ln] + [p for ft in osm['features'] for p in ft['pts']]
minx = min(p[0] for p in pts); maxx = max(p[0] for p in pts)
miny = min(p[1] for p in pts); maxy = max(p[1] for p in pts)
S = 0.3
W = int((maxx - minx) * S) + 60; H = int((maxy - miny) * S) + 60
def px(p):
    return (30 + (p[0] - minx) * S, H - 30 - (p[1] - miny) * S)
img = Image.new('RGB', (W, H), (18, 18, 22))
dr = ImageDraw.Draw(img)
# OSM taxiways
for ft in osm['features']:
    if ft['kind'] == 'taxiway':
        dr.line([px(p) for p in ft['pts']], fill=(60, 120, 180), width=2)
    elif ft['kind'] in ('terminal', 'transportation'):
        dr.polygon([px(p) for p in ft['pts']], fill=None, outline=(80, 200, 120))
    elif ft['kind'] == 'runway':
        dr.line([px(p) for p in ft['pts']], fill=(0, 255, 0), width=2)
# chart buildings
for ln in f['buildings']:
    dr.polygon([px(p) for p in ln], outline=(255, 200, 60))
img.save(os.path.join(REF, 'ref', 'derived', 'overlay_osm_chart.png'))
print(img.size)
