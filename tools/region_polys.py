# -*- coding: utf-8 -*-
"""List chart building polygons inside a region; render them colored with ids."""
import json, os, sys
from PIL import Image, ImageDraw
REF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ch = json.load(open(os.path.join(REF, 'ref', 'derived', 'chart_enu.json'), encoding='utf-8'))
bs = ch['features']['buildings']
x0, y0, x1, y1 = (float(v) for v in sys.argv[1:5]) if len(sys.argv) > 4 else (-200, -500, 700, 600)
sel = []
for i, ln in enumerate(bs):
    xs = [p[0] for p in ln]; ys = [p[1] for p in ln]
    if min(xs) >= x0 and max(xs) <= x1 and min(ys) >= y0 and max(ys) <= y1:
        sel.append((i, ln, max(xs) - min(xs), max(ys) - min(ys)))
sel.sort(key=lambda t: -(t[2] * t[3]))
print('region polygons:', [(i, round(w), round(h), len(ln)) for i, ln, w, h in sel])
if not sel:
    sys.exit()
pts = [p for _, ln, _, _ in sel for p in ln]
minx = min(p[0] for p in pts); maxx = max(p[0] for p in pts)
miny = min(p[1] for p in pts); maxy = max(p[1] for p in pts)
S = 0.9
W = int((maxx - minx) * S) + 60; H = int((maxy - miny) * S) + 60
def px(p):
    return (30 + (p[0] - minx) * S, H - 30 - (p[1] - miny) * S)
img = Image.new('RGB', (W, H), (15, 15, 18))
dr = ImageDraw.Draw(img)
cols = [(235, 205, 110), (110, 200, 220), (220, 120, 160), (150, 220, 140), (200, 160, 240)]
for k, (i, ln, w, h) in enumerate(sel):
    dr.polygon([px(p) for p in ln], fill=cols[k % 5], outline=(255, 255, 255))
    cx = sum(p[0] for p in ln) / len(ln); cy = sum(p[1] for p in ln) / len(ln)
    dr.text(px((cx, cy)), str(i), fill=(0, 0, 0))
img.save(os.path.join(REF, 'ref', 'derived', 't2_region.png'))
print(W, H)
