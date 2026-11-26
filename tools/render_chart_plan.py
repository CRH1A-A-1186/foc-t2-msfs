# -*- coding: utf-8 -*-
"""Render chart_enu.json features to a plan PNG (metres, x east, y north)."""
import json, os
from PIL import Image, ImageDraw

REF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(REF, 'ref', 'derived', 'chart_enu.json'), encoding='utf-8'))
f = d['features']
allpts = [p for k in f for ln in f[k] for p in ln]
minx = min(p[0] for p in allpts); maxx = max(p[0] for p in allpts)
miny = min(p[1] for p in allpts); maxy = max(p[1] for p in allpts)
S = 0.28
W = int((maxx - minx) * S) + 60; H = int((maxy - miny) * S) + 60
def px(p):
    return (30 + (p[0] - minx) * S, H - 30 - (p[1] - miny) * S)
img = Image.new('RGB', (W, H), (25, 25, 28))
dr = ImageDraw.Draw(img)
for ln in f['pavement']:
    dr.polygon([px(p) for p in ln], fill=(90, 80, 60), outline=(150, 140, 100))
for ln in f['buildings']:
    dr.polygon([px(p) for p in ln], fill=(200, 170, 90), outline=(255, 255, 255))
for ln in f['markings']:
    dr.line([px(p) for p in ln], fill=(200, 200, 210), width=1)
# runway reference lines (real coords) for validation
def enu(lat, lon):
    import math
    R = 6378137.0
    return (math.radians(lon - d['origin'][1]) * R * math.cos(math.radians(d['origin'][0])),
            math.radians(lat - d['origin'][0]) * R)
for (a, b) in [((25.920435, 119.655359), (25.949340, 119.671631)),
               ((25.910695, 119.671442), (25.940682, 119.688259))]:
    p, q = enu(*a), enu(*b)
    dr.line([px(p), px(q)], fill=(0, 255, 0), width=3)
img.save(os.path.join(REF, 'ref', 'derived', 'chart_plan.png'))
print(img.size, [round(minx), round(maxx), round(miny), round(maxy)])
