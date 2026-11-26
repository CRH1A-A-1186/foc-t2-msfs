# -*- coding: utf-8 -*-
"""r6 T2 roof: thin curved plate (constant-thickness shell) -- geometry only, no bpy.

Why a distance-field heightfield:
  The old roof was a loft between the eave ring and a shrunk ring, closed by a flat
  bottom cap -> the cross-section was a 14 m thick wedge ("lid").  Insetting a second
  ring toward the inside pinched at the concave corners and self-intersected.  A
  heightfield z = f(x, y) over the footprint is single valued by construction, so it
  cannot self-intersect; offsetting it straight down by T gives a plate whose section
  is the blade in the reference photo (thin at the eave, arcing to the crown).

  Outline is exact: each grid cell is cut against the true eave polygon (shapely) and
  triangulated; shared cut points weld to 1 mm -> watertight, no T-junctions, the eave
  follows the footprint offset to the millimetre.

  Height field:  z = TOP_EAVE + (R(p)*g(u) + tip_up(p)*g(u)),  u = d / D(p)
    d   = distance to the eave outline (common field -> one continuous shell)
    D   = measured half-width of the region (hall vs pier arms) -> no flat plateau
    g   = smoothstep, zero-slope at the eave (flat cantilever soffit) and at the crown
    R   = rise: hall 12.35 (crown 39.70), arms 5.5, plus upturn at the pier tips

Output: build/roof.json  {roof:{verts,faces,n_smooth}, pv:{...}, stats, section}
"""
import json, os, sys, math
_TOOLS = os.path.dirname(os.path.abspath(__file__))
for _d in ('pylib', 'pylib313'):          # cp313 build for Blender's python, cp312 fallback
    sys.path.insert(0, os.path.join(_TOOLS, _d))
from shapely.geometry import Polygon, Point

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEO = json.load(open(os.path.join(ROOT, 'build', 'geo.json'), encoding='utf-8'))
OUT = os.path.join(ROOT, 'build', 'roof.json')

# ---------------------------------------------------------------- plate spec
T_ROOF = 1.40        # plate thickness -> this is the section thickness at the eave
SOFFIT_E = 25.95     # underside at the eave, 0.30 m below the glass head (26.25)
TOP_EAVE = SOFFIT_E + T_ROOF
R_HALL = 12.35       # hall rise -> top at the crown = 27.35 + 12.35 = 39.70 (spec)
R_ARM = 5.50         # pier arms are much lower
FLAT = 12.0          # flat soffit band from the eave (the cantilever, no rise yet)
BLEND_S = 150.0      # hall -> arm blend length (distance away from the hall polygon)
UPLIFT = 3.00        # upturn at the pier tips
TIP_S = 0.30         # last 30 % of the hall distance gets the upturn
STEP = 7.0           # grid cell (m)
PV_LIFT = 0.30       # PV patch floats 0.30 m above the roof skin (no z-fighting)

AX_DEG = GEO['t2_rings']['axis_deg']

EAVE = Polygon(GEO['t2_rings']['eave'])
if EAVE.geom_type != 'Polygon':
    EAVE = max(EAVE.geoms, key=lambda g: g.area)
EAVE = Polygon(EAVE.exterior)
HALL = Polygon(GEO['t2_parts']['hall']['ring'])
if HALL.geom_type != 'Polygon':
    HALL = max(HALL.geoms, key=lambda g: g.area)
HALL = Polygon(HALL.exterior)
BND = EAVE.boundary

# ---------------------------------------------------------------- fields
def smoothstep(t):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)

def region_w(x, y):
    """0 inside the main hall, 1 well out over the pier arms."""
    return smoothstep(HALL.distance(Point(x, y)) / BLEND_S)

# half-width of each volume, measured against its OWN polygon (the y=250 cut is
# interior to the shell, so it must not inflate the arm half-width)
PARTS = {}
for _k in ('hall', 'pierA', 'pierB'):
    _p = GEO['t2_parts'].get(_k)
    if _p:
        _q = Polygon(_p['ring'])
        if _q.geom_type != 'Polygon':
            _q = max(_q.geoms, key=lambda g: g.area)
        PARTS[_k] = Polygon(_q.exterior)
_coarse = []
_ux0, _uy0, _ux1, _uy1 = EAVE.bounds
_g = 8.0
_y = _uy0 + _g / 2
while _y < _uy1:
    _x = _ux0 + _g / 2
    while _x < _ux1:
        if EAVE.contains(Point(_x, _y)):
            _coarse.append((_x, _y))
        _x += _g
    _y += _g
_dmax = {}
for _pt in _coarse:
    for _k, _q in PARTS.items():
        if _q.contains(Point(_pt)):
            _dd = _q.boundary.distance(Point(_pt))
            if _dd > _dmax.get(_k, 0.0):
                _dmax[_k] = _dd
            break
D_HALL = _dmax.get('hall', 60.0)
D_ARM = max([_dmax.get('pierA', 0.0), _dmax.get('pierB', 0.0)] or [45.0]) or 45.0
SMAX = max(BND.distance(Point(x, y)) for x, y in _coarse)

def z_top(x, y, d):
    w = region_w(x, y)
    D = D_HALL + (D_ARM - D_HALL) * w
    R = R_HALL + (R_ARM - R_HALL) * w
    u0 = FLAT / D
    u = d / D
    g = smoothstep((u - u0) / (1.0 - u0))
    s = HALL.distance(Point(x, y))
    up = UPLIFT * smoothstep((s - (1.0 - TIP_S) * SMAX) / (TIP_S * SMAX))
    return TOP_EAVE + (R + up) * g

# ---------------------------------------------------------------- mesher
def pieces(g):
    if g.is_empty:
        return []
    if g.geom_type == 'Polygon':
        return [g]
    if g.geom_type in ('MultiPolygon', 'GeometryCollection'):
        return [q for q in g.geoms if q.geom_type == 'Polygon' and q.area > 1e-9]
    return []

def is_convex(ring):
    n = len(ring)
    if n < 4:
        return True
    sign = 0
    for i in range(n):
        a, b, c = ring[i], ring[(i + 1) % n], ring[(i + 2) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) < 1e-12:
            continue
        s = 1 if cr > 0 else -1
        if sign == 0:
            sign = s
        elif s != sign:
            return False
    return True

def ring_tris(ring):
    """Triangle coordinate triples covering the polygon ring."""
    from shapely.ops import triangulate
    n = len(ring)
    if n == 3:
        return [list(ring)]
    if is_convex(ring):
        if n == 4:
            return [[ring[0], ring[1], ring[2]], [ring[0], ring[2], ring[3]]]
        return [[ring[0], ring[i], ring[i + 1]] for i in range(1, n - 1)]
    pg = Polygon(ring)
    tris = []
    for tri in triangulate(pg):
        if pg.contains(tri.centroid):
            tris.append(list(tri.exterior.coords)[:3])
    got = sum(abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2.0
              for a, b, c in tris) if tris else 0.0
    if pg.area > 1e-9 and abs(got - pg.area) > 0.01 * pg.area:
        cx, cy = pg.centroid.x, pg.centroid.y
        tris = [[(cx, cy), ring[i], ring[(i + 1) % n]] for i in range(n)]
        tris = [t for t in tris
                if abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1])
                       - (t[1][1] - t[0][1]) * (t[2][0] - t[0][0])) > 1e-9]
    return tris

def smooth_zt(faces, zt, fixed, iters, lam, zref, ztarget):
    """Laplacian relaxation of the height field.

    A raw distance field has creases along its medial axis (the ridge bifurcates),
    which reads as dents in the shading.  A few relaxation passes round those into
    one smooth crown.  The eave ring is pinned (exact outline, exact eave thickness)
    and the excess above the eave is rescaled so the crown still hits the spec height.
    """
    nbr = [[] for _ in zt]
    for f in faces:
        for k in range(len(f)):
            a_, b_ = f[k], f[(k + 1) % len(f)]
            nbr[a_].append(b_)
            nbr[b_].append(a_)
    z = list(zt)
    for _ in range(iters):
        nz = list(z)
        for i in range(len(z)):
            if i in fixed or not nbr[i]:
                continue
            s = sum(z[j] for j in nbr[i]) / float(len(nbr[i]))
            nz[i] = z[i] + lam * (s - z[i])
        z = nz
    hi = max(z)
    if hi > zref + 1e-6 and ztarget > zref:
        k = (ztarget - zref) / (hi - zref)
        z = [zref + (v - zref) * k for v in z]
    return z

def build(poly, step, zfun, shell=True, t_thick=0.0, zfix=0.0,
          iters=0, lam=0.5, zref=0.0, ztarget=0.0):
    """Cut-cell heightfield mesh over `poly`.

    Returns (verts, faces, n_smooth, meta); the first n_smooth faces are the skin
    (top + bottom), the rest are the eave rim quads.
    """
    c = poly.centroid
    a = math.radians(AX_DEG)
    ca, sa = math.cos(a), math.sin(a)
    def w2l(x, y):
        dx, dy = x - c.x, y - c.y
        return dx * ca + dy * sa, -dx * sa + dy * ca
    def l2w(u, v):
        return c.x + u * ca - v * sa, c.y + u * sa + v * ca

    us, vs = zip(*[w2l(x, y) for x, y in poly.exterior.coords])
    lu0, lu1, lv0, lv1 = min(us), max(us), min(vs), max(vs)
    nu = max(1, int(math.ceil((lu1 - lu0) / step)))
    nv = max(1, int(math.ceil((lv1 - lv0) / step)))
    du = (lu1 - lu0) / nu
    dv = (lv1 - lv0) / nv

    key2i, vxy = {}, []
    def vid(x, y):
        k = (round(x, 3), round(y, 3))
        i = key2i.get(k)
        if i is None:
            i = len(vxy)
            key2i[k] = i
            vxy.append((x, y))
        return i

    top_faces, used = [], 0
    for i in range(nu):
        u0 = lu0 + i * du
        for j in range(nv):
            v0 = lv0 + j * dv
            corners = [l2w(u0, v0), l2w(u0 + du, v0), l2w(u0 + du, v0 + dv), l2w(u0, v0 + dv)]
            for pg in pieces(poly.intersection(Polygon(corners))):
                if pg.area < 0.05:
                    continue
                if pg.interiors:
                    pg = Polygon(pg.exterior)
                ring = [(x, y) for x, y in list(pg.exterior.coords)[:-1]]
                if len(ring) < 3:
                    continue
                for t in ring_tris(ring):
                    tri = [vid(p[0], p[1]) for p in t]
                    if len(set(tri)) == 3:
                        top_faces.append(tri)
                used += 1

    n = len(vxy)
    zt = [zfun(x, y, BND.distance(Point(x, y))) for x, y in vxy]
    meta = {'cells': used}
    if not shell:
        verts = [[x, y, z + zfix] for (x, y), z in zip(vxy, zt)]
        faces = [list(f) for f in top_faces]
        return verts, faces, len(faces), meta

    # rim edges (used once by the skin) -> their verts pin the eave during relaxation
    count = {}
    for f in top_faces:
        for k in range(len(f)):
            a_, b_ = f[k], f[(k + 1) % len(f)]
            e = (a_, b_) if a_ < b_ else (b_, a_)
            count[e] = count.get(e, 0) + 1
    rim_edges = [e for e, c in count.items() if c == 1]
    fixed = set()
    for a_, b_ in rim_edges:
        fixed.add(a_)
        fixed.add(b_)
    if iters:
        zt = smooth_zt(top_faces, zt, fixed, iters, lam, zref, ztarget)

    verts = [[x, y, z + zfix] for (x, y), z in zip(vxy, zt)]
    faces = [list(f) for f in top_faces]
    verts += [[x, y, z + zfix - t_thick] for (x, y), z in zip(vxy, zt)]
    faces += [list(reversed([i + n for i in f])) for f in top_faces]
    n_smooth = len(faces)

    rim = 0
    for (a_, b_) in rim_edges:
        faces.append([a_, a_ + n, b_ + n, b_])
        rim += 1
    meta['rim_quads'] = rim
    meta['n_pinned'] = len(fixed)
    return verts, faces, n_smooth, meta

# ---------------------------------------------------------------- build roof
SMOOTH_ITERS = 12     # rounds the medial-axis creases of the raw distance field
SMOOTH_LAM = 0.50
rv, rf, rns, rst = build(EAVE, STEP, z_top, shell=True, t_thick=T_ROOF,
                         iters=SMOOTH_ITERS, lam=SMOOTH_LAM,
                         zref=TOP_EAVE, ztarget=TOP_EAVE + R_HALL)

# ---------------------------------------------------------------- PV band
# Deferred: the band must be re-authored as a patch that follows the relaxed surface
# (built from the analytic field it would float/poke after relaxation), so r6 ships
# without it rather than with a pasted-looking quad.
pv_v, pv_f, pv_ns, pv_area = [], [], 0, 0

# ---------------------------------------------------------------- section probe
# sampled from the finished mesh (nearest top-skin vertex), so the numbers are the
# geometry that is actually in the .blend
NT = len(rv) // 2
topv = [(rv[i][0], rv[i][1], rv[i][2]) for i in range(NT)]
hc = HALL.centroid
a = math.radians(AX_DEG)
nx, ny = -math.sin(a), math.cos(a)
sect = []
for k in range(-130, 131, 5):
    x, y = hc.x + nx * k, hc.y + ny * k
    if not EAVE.contains(Point(x, y)):
        continue
    best, bd = None, 1e18
    for (vx, vy, vz) in topv:
        dd = (vx - x) ** 2 + (vy - y) ** 2
        if dd < bd:
            bd, best = dd, (vx, vy, vz)
    sect.append({'s': k, 'ztop': round(best[2], 2), 'zbot': round(best[2] - T_ROOF, 2),
                 't': T_ROOF, 'snap_m': round(bd ** 0.5, 2)})

stats = dict(rst)
xsv = [v[0] for v in rv]; ysv = [v[1] for v in rv]; zsv = [v[2] for v in rv]
stats.update({
    'verts': len(rv), 'faces': len(rf), 'tris': sum(len(f) - 2 for f in rf),
    'n_smooth_faces': rns,
    'bbox': [round(min(xsv), 2), round(min(ysv), 2), round(min(zsv), 3),
             round(max(xsv), 2), round(max(ysv), 2), round(max(zsv), 3)],
    'height_m': round(max(zsv), 3), 'thickness_m': T_ROOF,
    'soffit_eave_m': SOFFIT_E, 'top_eave_m': round(TOP_EAVE, 3),
    'd_hall': round(D_HALL, 2), 'd_arm': round(D_ARM, 2), 's_max': round(SMAX, 2),
    'eave_out_m': 5.0, 'glass_inset_m': 3.0,
    'pv_area_m2': round(pv_area), 't2_area_m2': round(EAVE.area),
    'perimeter_m': round(EAVE.length),
})
json.dump({'params': {'T': T_ROOF, 'TOP_EAVE': TOP_EAVE, 'R_HALL': R_HALL, 'R_ARM': R_ARM,
                      'FLAT': FLAT, 'D_HALL': round(D_HALL, 2), 'D_ARM': round(D_ARM, 2),
                      'UPLIFT': UPLIFT, 'STEP': STEP},
           'roof': {'verts': rv, 'faces': rf, 'n_smooth': rns},
           'pv': {'verts': pv_v, 'faces': pv_f, 'n_smooth': pv_ns},
           'stats': stats, 'section': sect},
          open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)

print('ROOF ' + json.dumps(stats, ensure_ascii=False))
print('SECT ' + json.dumps(sect[::4], ensure_ascii=False))
