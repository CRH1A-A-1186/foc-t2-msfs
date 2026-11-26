# -*- coding: utf-8 -*-
"""Render large chart building polygons (auto) with indices; optionally filter by bbox."""
import json, os, sys
from PIL import Image, ImageDraw
REF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ch = json.load(open(os.path.join(REF, 'ref', 'derived', 'chart_enu.json'), encoding='utf-8'))
bs = ch['features']['buildings']
min_size = float(sys.argv[1]) if len(sys.argv) > 1 else 300.0
sel = []
for i, ln in enumerate(bs):
    xs = [p[0] for p in ln]; ys = [p[1] for p in ln]
    if max(xs) - min(xs) > min_size or max(ys) - min(ys) > min_size:
        sel.append((i, ln, max(xs) - min(xs), max(ys) - min(ys)))
sel.sort(key=lambda t: -(t[2] * t[3]))
pts = [p for _, ln, _, _ in sel for p in ln]
minx = min(p[0] for p in pts); maxx = max(p[0] for p in pts)
miny = min(p[1] for p in pts); maxy = max(p[1] for p in pts)
S = 0.28
W = int((maxx - minx) * S) + 60; H = int((maxy - miny) * S) + 60
def px(p):
    return (30 + (p[0] - minx) * S, H - 30 - (p[1] - miny) * S)
img = Image.new('RGB', (W, H), (16, 16, 20))
dr = ImageDraw.Draw(img)
cols = [(220, 190, 100), (120, 200, 160), (200, 120, 160), (140, 160, 230)]
for k, (i, ln, w, h) in enumerate(sel):
    dr.polygon([px(p) for p in ln], fill=cols[k % 4], outline=(255, 255, 255))
    cx = sum(p[0] for p in ln) / len(ln); cy = sum(p[1] for p in ln) / len(ln)
    dr.text(px((cx, cy)), f'{i}', fill=(20, 20, 20))
img.save(os.path.join(REF, 'ref', 'derived', 'bld_big.png'))
print('picked', [(i, round(w), round(h)) for i, _, w, h in sel])
print(W, H)
