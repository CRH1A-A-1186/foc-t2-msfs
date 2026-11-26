# -*- coding: utf-8 -*-
"""Assemble project geometry (ENU metres) -> build/geo.json for the Blender builder.

Sources
  OSM (Overpass 2026-07-28): taxiway centre lines, apron polygons, runway centre lines
  CAAC AIP apron chart 2P-1 (AIRAC 11/26): T2 footprint (vector-traced), scale check
Coordinates: x = east, y = north, metres, origin = ARP 25.929254N 119.672524E
"""
import json, os, math, sys
for _d in ('pylib', 'pylib313'):      # cp313 (Blender python) first, cp312 fallback
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), _d))
from shapely.geometry import LineString, Polygon, Point, MultiLineString, MultiPolygon
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, 'ref', 'derived')
os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)

TAXI_W = 23.0      # ICAO code E/F straight taxiway width (m)
RWY_W = 45.0       # runway width
SHOULDER = 15.0    # paved shoulder each side

osm = json.load(open(os.path.join(DER, 'osm_plan.json'), encoding='utf-8'))
ch = json.load(open(os.path.join(DER, 'chart_enu.json'), encoding='utf-8'))
feats = osm['features']

def rings(g, holes=True):
    """Polygonal geometry -> [{'outer': [...], 'holes': [[...], ...]}, ...].

    Holes matter: the pavement layers are built by subtracting (apron - runway -
    taxiway), so the apron is a polygon WITH holes.  Dropping the holes made the
    apron cover the taxiways again -> coplanar overlap at z=0 -> the z-fighting
    (and the "shattered" patches) seen in the viewport.
    """
    out = []
    if g.is_empty:
        return out
    geoms = list(g.geoms) if hasattr(g, 'geoms') else [g]
    for p in geoms:
        if p.geom_type == 'Polygon':
            out.append({'outer': [[round(x, 2), round(y, 2)] for x, y in p.exterior.coords],
                        'holes': ([[[round(x, 2), round(y, 2)] for x, y in ir.coords]
                                   for ir in p.interiors] if holes else [])})
        elif p.geom_type == 'MultiPolygon':
            out += rings(p, holes)
    return out

# --- taxiways
taxi_lines = [f for f in feats if f['kind'] == 'taxiway' and len(f['pts']) >= 2]
taxi_geoms = [LineString(f['pts']) for f in taxi_lines]
taxi_buf = unary_union([g.buffer(TAXI_W / 2, cap_style=2, join_style=2) for g in taxi_geoms])
taxi_buf = taxi_buf.buffer(0)

# --- aprons (OSM)
apron_polys = []
for f in feats:
    if f['kind'] != 'apron' or len(f['pts']) < 3:
        continue
    p = Polygon(f['pts'])
    if not p.is_valid:
        p = p.buffer(0)
    apron_polys.append(p)
apron = unary_union([p for p in apron_polys if p.area > 2000]).buffer(0)

# --- runways (45 m + shoulders)
rwy_polys = []
rwy_lines = []
for f in feats:
    if f['kind'] != 'runway' or len(f['pts']) < 2:
        continue
    L = LineString(f['pts'])
    if L.length < 1500:
        continue
    rwy_lines.append(f)
    rwy_polys.append(L.buffer(RWY_W / 2 + SHOULDER, cap_style=2, join_style=2))
rwy = unary_union(rwy_polys).buffer(0)

# --- T2 footprint from chart (polygon #14 = largest inside terminal region)
bs = ch['features']['buildings']
best = None
for ln in bs:
    xs = [p[0] for p in ln]; ys = [p[1] for p in ln]
    if max(xs) - min(xs) > 500 and max(ys) - min(ys) > 500:
        if -300 < sum(xs) / len(xs) < 600 and -300 < sum(ys) / len(ys) < 400:
            if best is None or len(ln) > len(best):
                best = ln
t2 = Polygon(best).buffer(0)
if t2.geom_type != 'Polygon':
    t2 = max(t2.geoms, key=lambda g: g.area)
t2 = Polygon(t2.exterior.coords).simplify(0.8)

# --- pavement: planar partition (disjoint layers -> no coplanar z-fighting)
t2_apron = t2.buffer(115.0).buffer(0)
ground_raw = unary_union([taxi_buf, apron, rwy, t2_apron]).buffer(0)
p_rwy = rwy.buffer(0)
p_twy = taxi_buf.difference(p_rwy).buffer(0)
p_apron = unary_union([apron, t2_apron]).buffer(0).difference(p_rwy).difference(p_twy).buffer(0)
p_base = ground_raw.difference(p_rwy).difference(p_twy).difference(p_apron).buffer(0)
ground = ground_raw

mins = {}
def stat(name, g):
    b = g.bounds
    mins[name] = {'area_m2': round(g.area) if not g.is_empty else 0, 'bounds': [round(v, 1) for v in b] if not g.is_empty else []}

stat('taxiway', p_twy); stat('apron', p_apron); stat('runway', p_rwy); stat('t2', t2); stat('base', p_base)

# --- T2 derived rings for the 3D massing (offsets handled by shapely, robust on concave shapes)
def ring_of(g):
    p = g if g.geom_type == 'Polygon' else max(g.geoms, key=lambda q: q.area)
    p = p.simplify(0.7)
    return [[round(x, 2), round(y, 2)] for x, y in p.exterior.coords]

# r6: glass curtain wall recessed 3.0 m behind the podium face (deep eave shadow),
# roof plate cantilevered 5.0 m beyond the podium face -> 8.0 m clear overhang.
GLASS_INSET = 3.0
EAVE_OUT = 5.0
glass_r = ring_of(Polygon(t2.exterior).buffer(-GLASS_INSET).buffer(0))
eave_r = ring_of(Polygon(t2.exterior).buffer(EAVE_OUT).buffer(0))
# roof shell: nested rings by inset; local roof height driven by distance-to-facade
# (wide hall -> tall roof, narrow piers -> lower roof; matches the design render)
BOUND = Polygon(t2.exterior).boundary
def ring_dist(ring):
    return [round(min(1.0, BOUND.distance(Point(x, y)) / 60.0), 4) for x, y in ring]
shell_rings = {}
_cx = sum(p[0] for p in t2.exterior.coords[:-1]) / (len(t2.exterior.coords) - 1)
_cy = sum(p[1] for p in t2.exterior.coords[:-1]) / (len(t2.exterior.coords) - 1)
_t2p = Polygon(t2.exterior)
def dist_to_facade(pt):
    return _t2p.boundary.distance(Point(pt[0], pt[1]))
for name, s in (('r0', 1.0), ('r1', 0.94), ('r2', 0.88), ('r3', 0.82)):
    rr = [[round(_cx + (x - _cx) * s, 2), round(_cy + (y - _cy) * s, 2)]
          for x, y in t2.exterior.coords[:-1]]
    rr.append(rr[0])
    shell_rings[name] = {'ring': rr, 's': s, 'd': [round(dist_to_facade(q), 2) for q in rr]}
# long axis (PCA) -> t in [0,1] for the saddle roof
import math as _m
pts = t2.exterior.coords[:-1]
mx = sum(p[0] for p in pts) / len(pts); my = sum(p[1] for p in pts) / len(pts)
sxx = sum((p[0] - mx) ** 2 for p in pts); syy = sum((p[1] - my) ** 2 for p in pts)
sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
ang = 0.5 * _m.atan2(2 * sxy, sxx - syy)
ax, ay = _m.cos(ang), _m.sin(ang)
proj = [((p[0] - mx) * ax + (p[1] - my) * ay) for p in pts]
pmin, pmax = min(proj), max(proj)
# PV skylight band: 70 m wide strip along the long axis, clipped to the footprint
_axis_line = LineString([(mx + ax * pmin, my + ay * pmin), (mx + ax * pmax, my + ay * pmax)])
_pv = Polygon(t2.exterior).intersection(_axis_line.buffer(35, cap_style=2))
if _pv.is_empty:
    pv_band = {'ring': [], 'd': []}
else:
    if _pv.geom_type != 'Polygon':
        _pv = max(_pv.geoms, key=lambda g: g.area)
    pv_band = {'ring': [[round(x, 2), round(y, 2)] for x, y in _pv.exterior.coords],
               'd': [round(dist_to_facade(q), 2) for q in _pv.exterior.coords],
               'area_m2': round(_pv.area)}
def tvals(ring):
    out_t = []
    for x, y in ring:
        v = (x - mx) * ax + (y - my) * ay
        out_t.append(round((v - pmin) / max(1e-6, pmax - pmin), 4))
    return out_t

def base_ring_scaled(ring, s):
    pts = ring[:-1] if ring[0] == ring[-1] else ring
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    o = [[round(cx + (x - cx) * s, 2), round(cy + (y - cy) * s, 2)] for x, y in pts]
    o.append(o[0])
    return o


# --- split T2 into main hall + two piers
def band_width(y, half=12.0):
    band = Polygon([(-2000, y - half), (2000, y - half), (2000, y + half), (-2000, y + half)])
    g = Polygon(t2.exterior).intersection(band)
    if g.is_empty:
        return 0.0
    b = g.bounds
    return b[2] - b[0]

ys = [480 - i * 10 for i in range(95)]
ws = [band_width(y) for y in ys]
cut_y = None
best = 0.0
for i in range(6, len(ys) - 6):
    drop = (ws[i - 5] + ws[i - 4] + ws[i - 3]) / 3.0 - (ws[i + 3] + ws[i + 4] + ws[i + 5]) / 3.0
    if drop > best and ws[i] < 0.9 * max(ws):
        best = drop
        cut_y = ys[i]
if cut_y is None:
    cut_y = 0.0
rect_n = Polygon([(-2000, cut_y), (2000, cut_y), (2000, 2000), (-2000, 2000)])
rect_s = Polygon([(-2000, -2000), (2000, -2000), (2000, cut_y), (-2000, cut_y)])
hall = Polygon(t2.exterior).intersection(rect_n)
arms = Polygon(t2.exterior).intersection(rect_s)

def poly_list(g):
    if g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    return [q for q in g.geoms if q.geom_type == 'Polygon' and q.area > 500]

# split the two piers: find the courtyard gap (a y where the section has two intervals)
gap_x = None
for yy in [200 - i * 10 for i in range(45)]:
    band = Polygon([(-2000, yy - 6), (2000, yy - 6), (2000, yy + 6), (-2000, yy + 6)])
    sec = Polygon(t2.exterior).intersection(band)
    comps = poly_list(sec)
    if len(comps) == 2:
        xa = max(comps[0].bounds[2], comps[1].bounds[2])
        xb = min(comps[0].bounds[0], comps[1].bounds[0])
        gap_x = (xa + xb) / 2.0 if xa < xb else (comps[0].centroid.x + comps[1].centroid.x) / 2.0
        break
if gap_x is None:
    gap_x = arms.centroid.x
cut_x = round(gap_x, 1)
rect_w = Polygon([(-4000, -4000), (cut_x, -4000), (cut_x, 4000), (-4000, 4000)])
rect_e = Polygon([(cut_x, -4000), (4000, -4000), (4000, 4000), (cut_x, 4000)])
parts = {'hall': hall}
for tag, hp in (('pierA', rect_w), ('pierB', rect_e)):
    g = arms.intersection(hp)
    if not g.is_empty:
        g = max(poly_list(g), key=lambda q: q.area)
        if g.area > 3000:
            parts[tag] = g

t2_parts = {}
for name, g in parts.items():
    if g.is_empty:
        continue
    g = g.buffer(0)
    if g.geom_type != 'Polygon':
        g = max(g.geoms, key=lambda q: q.area)
    gs = g.simplify(0.7)
    rr = [[round(x, 2), round(y, 2)] for x, y in gs.exterior.coords]
    outer = base_ring_scaled(rr, 1.02)
    inner = base_ring_scaled(rr, 0.80 if name != 'hall' else 0.86)
    t2_parts[name] = {
        'ring': rr,
        'eave': outer,
        'top': inner,
        'd': [round(dist_to_facade(q), 2) for q in inner],
        'area_m2': round(g.area),
        'bbox': [round(v, 1) for v in g.bounds],
    }
out = {
    'crs': 'ENU metres, origin = ARP, x=east, y=north, z=up',
    'axis': {'ox': round(mx, 2), 'oy': round(my, 2), 'ax': round(ax, 6), 'ay': round(ay, 6),
             'pmin': round(pmin, 2), 'pmax': round(pmax, 2)},
    'pv_band': pv_band,
    't2_parts': t2_parts,
    't2_cut_y': round(cut_y, 1),
    't2_rings': {'base': ring_of(t2), 'glass': glass_r, 'eave': eave_r, 'shell': shell_rings,
                 'axis_deg': round(_m.degrees(ang), 3), 'length_m': round(pmax - pmin, 1)},
    'origin': osm['origin'],
    'params': {'taxi_width_m': TAXI_W, 'rwy_width_m': RWY_W, 'shoulder_m': SHOULDER},
    'pavement': {
        'taxiway': rings(p_twy),
        'apron': rings(p_apron),
        'runway': rings(p_rwy),
        'ground': rings(p_base),
    },
    'lines': {
        'taxi_center': [[[round(x, 2), round(y, 2)] for x, y in f['pts']] for f in taxi_lines
                        if LineString(f['pts']).length >= 120.0],
    },
    't2': {'ring': [[round(x, 2), round(y, 2)] for x, y in t2.exterior.coords],
           'area_m2': round(t2.area), 'perimeter_m': round(t2.length)},
    'stats': mins,
    'sources': {
        'osm': 'OpenStreetMap via Overpass API 2026-07-28 (ways: aeroway=taxiway/apron/runway/terminal)',
        'chart': 'CAAC AIP 2P-1 ZSFZ aircraft parking chart AIRAC AMDT 11/26 (EFF 2026-10-28)',
        'runway_dims': 'OurAirports runways.csv (ZSFZ) + AD chart text: 3600x45 CONC both runways',
        't2_facts': 'T2 GFA ~255,000 m2, height 39.7 m, opened 2026-09-16 (public reports)',
    },
}
json.dump(out, open(os.path.join(ROOT, 'build', 'geo.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(json.dumps(out['stats'], indent=1, ensure_ascii=False))
print('t2 ring pts', len(out['t2']['ring']), 'taxi lines', len(out['lines']['taxi_center']))
print('->', os.path.join(ROOT, 'build', 'geo.json'))
