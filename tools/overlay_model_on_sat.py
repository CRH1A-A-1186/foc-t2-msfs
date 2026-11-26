# -*- coding: utf-8 -*-
"""Overlay model geometry (ENU metres) on a Google tile mosaic (georeferenced)."""
import json, math, os, sys
from PIL import Image, ImageDraw

ROOT = r"F:\dshproj\foc-t2"
MOS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'ref', 'sat', 'g_t2_z18.png')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'ref', 'derived', 'model_on_google.png')
geo = json.load(open(os.path.join(ROOT, 'build', 'geo.json'), encoding='utf-8'))
meta = json.load(open(os.path.splitext(MOS)[0] + '.json'))
ORG = geo['origin']
R = 6378137.0
Z = meta['zoom']
TX0, TY0 = meta['tile_x0'], meta['tile_y0']

def enu2ll(x, y):
    lat = ORG[0] + math.degrees(y / R)
    lon = ORG[1] + math.degrees(x / (R * math.cos(math.radians(ORG[0]))))
    return lat, lon

def ll2px(lat, lon):
    n = 2.0 ** Z
    tx = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    ty = (1.0 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2.0 * n
    return (tx - TX0) * 256.0, (ty - TY0) * 256.0

def to_px(pt):
    return ll2px(*enu2ll(pt[0], pt[1]))

img = Image.open(MOS).convert('RGB')
dr = ImageDraw.Draw(img, 'RGBA')

# T2 footprint + derived rings
for key, col in (('base', (255, 40, 40, 255)), ('eave', (255, 210, 0, 200))):
    ring = geo['t2_rings'][key]
    pts = [to_px(p) for p in ring]
    dr.line(pts, fill=col, width=5)

# taxiway centre lines
for ln in geo['lines']['taxi_center']:
    pts = [to_px(p) for p in ln]
    dr.line(pts, fill=(0, 255, 255, 190), width=3)

# runway edges (from pavement rings)
for ring in geo['pavement']['runway']:
    pts = [to_px(p) for p in ring]
    dr.line(pts, fill=(0, 255, 0, 230), width=4)

img.save(OUT)
print('->', OUT, img.size)
