# -*- coding: utf-8 -*-
"""Numeric checks: runway separation, chart vs OSM T1/T2 centroids, scale consistency."""
import json, os, math

REF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ch = json.load(open(os.path.join(REF, 'ref', 'derived', 'chart_enu.json'), encoding='utf-8'))
osm = json.load(open(os.path.join(REF, 'ref', 'derived', 'osm_plan.json'), encoding='utf-8'))
R = 6378137.0
ORG = ch['origin']

def enu(lat, lon):
    return (math.radians(lon - ORG[1]) * R * math.cos(math.radians(ORG[0])),
            math.radians(lat - ORG[0]) * R)

def line_pts(ft):
    return [enu(p['lat'], p['lon']) for p in ft['pts']] if False else ft['pts']

# real runways from OSM features (already ENU)
rw = [ft for ft in osm['features'] if ft['kind'] == 'runway']
print('runways:', [(f['ref'], len(f['pts'])) for f in rw])
def seg_stats(pts):
    import math as m
    L = sum(m.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    a, b = pts[0], pts[-1]
    brg = (m.degrees(m.atan2(b[0] - a[0], b[1] - a[1]))) % 360
    return L, brg
for f in rw:
    if len(f['pts']) == 2:
        continue
    L, brg = seg_stats(f['pts'])
    print(f"  rwy ref={f['ref']} len={L:.1f} m brg={brg:.2f} P0={tuple(round(v,1) for v in f['pts'][0])} Pn={tuple(round(v,1) for v in f['pts'][-1])}")

# perpendicular distance between the two main runways
l1 = [f for f in rw if f['ref'] == '03/21'][0]['pts'][0], [f for f in rw if f['ref'] == '03/21'][0]['pts'][-1]
l2 = [f for f in rw if f['ref'] == '04/22'][0]['pts'][0], [f for f in rw if f['ref'] == '04/22'][0]['pts'][-1]
import math as m
def perp(a, b, p):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    n = m.hypot(dx, dy)
    return abs((p[0] - ax) * dy - (p[1] - ay) * dx) / n
print('perp dist rwy04.first to rwy03 line: %.1f m' % perp(l1[0], l1[1], l2[0]))
print('perp dist rwy04.last  to rwy03 line: %.1f m' % perp(l1[0], l1[1], l2[1]))
print('chart runway separation (m):', round(315.7 * ch['scale_m_per_pt'], 1))

# chart buildings centroids
def centroid(ln):
    xs = [p[0] for p in ln]; ys = [p[1] for p in ln]
    return (sum(xs) / len(xs), sum(ys) / len(ys))
bigs = sorted(ch['features']['buildings'], key=lambda ln: -(max(p[0] for p in ln) - min(p[0] for p in ln)))
print('\nchart building bboxes (m, ENU):')
for ln in bigs[:8]:
    xs = [p[0] for p in ln]; ys = [p[1] for p in ln]
    print(f"  n={len(ln):<3} bbox x[{min(xs):.0f},{max(xs):.0f}] y[{min(ys):.0f},{max(ys):.0f}] size {max(xs)-min(xs):.0f}x{max(ys)-min(ys):.0f} centroid {centroid(ln)[0]:.0f},{centroid(ln)[1]:.0f}")

print('\nOSM terminals:')
for ft in osm['features']:
    if ft['kind'] in ('terminal', 'transportation'):
        xs = [p[0] for p in ft['pts']]; ys = [p[1] for p in ft['pts']]
        print(f"  {ft['ref']} n={len(ft['pts'])} bbox x[{min(xs):.0f},{max(xs):.0f}] y[{min(ys):.0f},{max(ys):.0f}] size {max(xs)-min(xs):.0f}x{max(ys)-min(ys):.0f} centroid {centroid(ft['pts'])[0]:.0f},{centroid(ft['pts'])[1]:.0f}")
