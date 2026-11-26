# -*- coding: utf-8 -*-
"""Summarize OSM aeroway data for ZSFZ: element counts, tags, lengths, bboxes."""
import json, math, sys
import os
from collections import Counter, defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

P = os.path.join(_ROOT, 'ref', 'zsfz_osm.json')
d = json.load(open(P, encoding='utf-8'))
els = d.get('elements', [])
print('elements', len(els), 'osm3s', d.get('osm3s'))
kinds = Counter(e['tags'].get('aeroway', '?') for e in els if e['type'] == 'way')
print('aeroway counts', dict(kinds))

def hav(a, b):
    R = 6378137.0
    lon1, lat1, lon2, lat2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlat = lat2 - lat1; dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))

def length(geom):
    return sum(hav((geom[i]['lon'], geom[i]['lat']), (geom[i + 1]['lon'], geom[i + 1]['lat'])) for i in range(len(geom) - 1))

print('\n== runways ==')
for e in els:
    t = e['tags']
    if t.get('aeroway') != 'runway':
        continue
    g = e['geometry']
    L = length(g)
    # bearing of straight line first->last
    lat1, lon1 = math.radians(g[0]['lat']), math.radians(g[0]['lon'])
    lat2, lon2 = math.radians(g[-1]['lat']), math.radians(g[-1]['lon'])
    brg = math.degrees(math.atan2(math.sin(lon2 - lon1) * math.cos(lat2),
                                  math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))) % 360
    print(f"id={e['id']} ref={t.get('ref')} len={L:.0f}m nodes={len(g)} brg={brg:.1f} width={t.get('width')} surf={t.get('surface')} name={t.get('name')}")
    print(f"   start=({g[0]['lat']:.6f},{g[0]['lon']:.6f}) end=({g[-1]['lat']:.6f},{g[-1]['lon']:.6f})")

print('\n== taxiway total length by ref ==')
agg = defaultdict(lambda: [0, 0.0])
for e in els:
    t = e['tags']
    if t.get('aeroway') != 'taxiway':
        continue
    ref = t.get('ref') or t.get('name') or '(unnamed)'
    agg[ref][0] += 1
    agg[ref][1] += length(e['geometry'])
for k, v in sorted(agg.items(), key=lambda kv: -kv[1][1])[:40]:
    print(f"  {k:>10}: ways={v[0]:<3} len={v[1]:7.0f}m")

print('\n== terminals / aprons ==')
for e in els:
    t = e['tags']
    if t.get('aeroway') in ('terminal', 'apron') or t.get('building') == 'terminal':
        g = e['geometry']
        lats = [p['lat'] for p in g]; lons = [p['lon'] for p in g]
        w = hav((min(lons), min(lats)), (max(lons), min(lats)))
        h = hav((min(lons), min(lats)), (min(lons), max(lats)))
        print(f"id={e['id']} {t.get('aeroway')} name={t.get('name')} nodes={len(g)} bbox={w:.0f}x{h:.0f}m tags={ {k: v for k, v in t.items() if k in ('aeroway','name','building','ref')} }")
