# -*- coding: utf-8 -*-
"""Render one OSM feature (terminal/apron) large with mm annotations, and dump its ring in metres."""
import json, math, sys, os
from PIL import Image, ImageDraw

P = r"F:\dshproj\foc-t2\ref\derived\osm_plan.json"
OUT = r"F:\dshproj\foc-t2\ref\derived"
feat_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1422594275
d = json.load(open(P, encoding='utf-8'))
f = next(x for x in d['features'] if x['id'] == feat_id)
pts = f['pts']
xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
S = 0.6
pad = 70
W = int((maxx - minx) * S) + 2 * pad
H = int((maxy - miny) * S) + 2 * pad
img = Image.new('RGB', (W, H), (18, 18, 20))
dr = ImageDraw.Draw(img)
def px(p):
    return (pad + (p[0] - minx) * S, H - pad - (p[1] - miny) * S)
ring = [px(p) for p in pts]
dr.polygon(ring, fill=(235, 205, 120), outline=(255, 255, 255))
for i, (x, y) in enumerate(ring):
    dr.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=(255, 60, 60))
    if i % 5 == 0:
        dr.text((x + 4, y - 4), f'{i}', fill=(200, 200, 255))
dr.line([px((minx, miny)), px((maxx, miny))], fill=(0, 255, 0), width=2)
dr.text((pad, H - pad + 20), f'span {maxx - minx:.0f} m  (x) / {maxy - miny:.0f} m (y)  pts={len(pts)}', fill=(0, 255, 0))
img.save(os.path.join(OUT, f'feat_{feat_id}.png'))
json.dump({'id': feat_id, 'kind': f['kind'], 'name': f['name'], 'pts': [[round(x, 2), round(y, 2)] for x, y in pts]},
          open(os.path.join(OUT, f'feat_{feat_id}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('size', [maxx - minx, maxy - miny], 'pts', len(pts), '->', os.path.join(OUT, f'feat_{feat_id}.png'))

