# -*- coding: utf-8 -*-
"""Transform ICAO apron-chart vectors into local ENU metres and export features.

Control: RWY03/21 drawn rectangle (#74) endpoints <-> real threshold coords.
Output: chart_enu.json {pavement:[polys], buildings:[polys], markings:[lines], runways:[...]}
"""
import json, math, os

REF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAW = os.path.join(REF, 'ref', 'apron', 'drawings.json')
OUT = os.path.join(REF, 'ref', 'derived', 'chart_enu.json')
ORIGIN = (25.929254, 119.672524)  # ARP
R = 6378137.0

# real RWY03/21 thresholds (OSM traced): SW end (03) -> NE end (21)
P03 = (25.920435, 119.655359)
P21 = (25.949340, 119.671631)

def enu(lat, lon):
    x = math.radians(lon - ORIGIN[1]) * R * math.cos(math.radians(ORIGIN[0]))
    y = math.radians(lat - ORIGIN[0]) * R
    return x, y

E03, E21 = enu(*P03), enu(*P21)

dr = json.load(open(DRAW, encoding='utf-8'))

def polys_of(d):
    """Flatten drawing items to list of polylines (each a list of (x,y) chart pts)."""
    lines, cur = [], []
    for it in d['items']:
        t = it[0]
        if t == 'l':
            p, q = tuple(it[1]), tuple(it[2])
            if not cur:
                cur = [p]
            cur.append(q)
        elif t == 'c':
            p1, p2, p3, p4 = [tuple(x) for x in it[1:5]]
            if not cur:
                cur = [p1]
            for k in range(1, 9):
                u = k / 8.0
                a = (1 - u) ** 3; b = 3 * (1 - u) ** 2 * u; c = 3 * (1 - u) * u * u; dd = u ** 3
                cur.append((a * p1[0] + b * p2[0] + c * p3[0] + dd * p4[0],
                            a * p1[1] + b * p2[1] + c * p3[1] + dd * p4[1]))
        elif t == 're':
            x0, y0, x1, y1 = it[1]
            if cur:
                lines.append(cur)
            lines.append([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
            cur = []
        elif t == 'qu':
            pts = [tuple(p) for p in it[1:5]]
            if cur:
                lines.append(cur)
            lines.append(pts + [pts[0]])
            cur = []
    if cur:
        lines.append(cur)
    return lines

# --- control points: runway 03 rectangle #74 -> (x=82.0 => 03, x=674.0 => 21)
rwy = dr[74]
pts = [p for ln in polys_of(rwy) for p in ln]
xs = [p[0] for p in pts]
x0c, x1c = min(xs), max(xs)
yc = sum(p[1] for p in pts) / len(pts)
A_chart = (x0c, yc); B_chart = (x1c, yc)
A_real, B_real = E03, E21

dx_c = B_chart[0] - A_chart[0]; dy_c = B_chart[1] - A_chart[1]
dx_r = B_real[0] - A_real[0]; dy_r = B_real[1] - A_real[1]
scale = math.hypot(dx_r, dy_r) / math.hypot(dx_c, dy_c)
ang_c = math.atan2(dy_c, dx_c)
ang_r = math.atan2(dy_r, dx_r)
rot = ang_r - ang_c
ca, sa = math.cos(rot), math.sin(rot)

def xf(p):
    x = (p[0] - A_chart[0]) * scale
    y = (p[1] - A_chart[1]) * scale
    ex = x * ca - y * sa + A_real[0]
    ey = x * sa + y * ca + A_real[1]
    return (ex, ey)

# chart y axis points DOWN (PDF), so flip y before rotation
def xf2(p):
    x = (p[0] - A_chart[0]) * scale
    y = (p[1] - A_chart[1]) * scale
    return xf((A_chart[0] + x / scale, A_chart[1] + y / scale))

def xf3(p):
    # chart coords: x right, y down. Real ENU: x east, y north.
    vx = (p[0] - A_chart[0]) * scale          # metres along runway dir
    vy = (p[1] - A_chart[1]) * scale          # metres "down" in chart = negative north
    # chart +x maps to real runway direction; chart +y (down) maps to real -perp?
    ex = vx * ca - (-vy) * sa
    ey = vx * sa + (-vy) * ca
    return (ex + A_real[0], ey + A_real[1])

print('scale m/pt', round(scale, 4), 'rot deg', round(math.degrees(rot), 3))
chk21 = xf3(B_chart)
print('check 21', (round(chk21[0] - E21[0], 2), round(chk21[1] - E21[1], 2)))

# --- export: pavement (fill 0.898), buildings (fill 0.502), markings (white 0.988)
def close_to(c, ref, tol=0.02):
    return c and all(abs(a - b) < tol for a, b in zip(c, ref))

feats = {'pavement': [], 'buildings': [], 'markings': [], 'runways': []}
for i, d in enumerate(dr):
    f = d.get('fill'); s = d.get('color')
    if f and close_to(f, (0.898,)) and d['type'] == 'f':
        key = 'pavement'
    elif f and close_to(f, (0.502,)) and d['type'] == 'f':
        key = 'buildings'
    elif f and close_to(f, (0.988,)) and d['type'] == 'f':
        key = 'markings'
    else:
        continue
    for ln in polys_of(d):
        if len(ln) < 2:
            continue
        feats[key].append([[round(c, 2) for c in xf3(p)] for p in ln])

json.dump({'origin': ORIGIN, 'scale_m_per_pt': scale, 'rot_deg': math.degrees(rot),
           'control': {'A_chart': A_chart, 'B_chart': B_chart, 'A_real': A_real, 'B_real': B_real},
           'features': feats}, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print({k: len(v) for k, v in feats.items()})
print('->', OUT)
