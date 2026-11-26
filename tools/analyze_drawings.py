# -*- coding: utf-8 -*-
"""Analyze chart vector drawings: group by fill/stroke, find big shapes (runways, terminals)."""
import json
import os
from collections import Counter

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

P = os.path.join(_ROOT, 'ref', 'apron', 'drawings.json')
dr = json.load(open(P, encoding='utf-8'))

def bbox(items):
    xs, ys = [], []
    for it in items:
        t = it[0]
        if t == 'l':
            xs += [it[1][0], it[2][0]]; ys += [it[1][1], it[2][1]]
        elif t == 'c':
            xs += [it[1][0], it[2][0], it[3][0], it[4][0]]
            ys += [it[1][1], it[2][1], it[3][1], it[4][1]]
        elif t == 're':
            r = it[1]
            xs += [r[0], r[2]]; ys += [r[1], r[3]]
        elif t == 'qu':
            for p in it[1:]:
                xs.append(p[0]); ys.append(p[1])
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))

rows = []
for idx, d in enumerate(dr):
    bb = bbox(d.get('items') or [])
    if not bb:
        continue
    rows.append((idx, d.get('type'),
                 tuple(round(c, 3) for c in d['fill']) if d.get('fill') else None,
                 tuple(round(c, 3) for c in d['color']) if d.get('color') else None,
                 round(d['width'], 2) if d.get('width') else None,
                 len(d.get('items') or []), bb))

print("== fill/type histogram (top 15) ==")
for k, v in Counter((r[1], r[2]) for r in rows).most_common(15):
    print(v, k)

print("\n== stroke histogram (top 15) ==")
for k, v in Counter((r[1], r[3], r[4]) for r in rows if r[1] == 's').most_common(15):
    print(v, k)

def area(r):
    x0, y0, x1, y1 = r[6]
    return (x1 - x0) * (y1 - y0)

print("\n== largest 30 filled shapes ==")
for r in sorted([r for r in rows if r[1] == 'f'], key=lambda r: -area(r))[:30]:
    x0, y0, x1, y1 = r[6]
    print(f"#{r[0]:<5} fill={r[2]} items={r[5]:<4} bbox=({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) size=({x1-x0:.1f}x{y1-y0:.1f})")

print("\n== long thin shapes (runway-like) ==")
cand = []
for r in rows:
    x0, y0, x1, y1 = r[6]
    w_, h_ = x1 - x0, y1 - y0
    L = max(w_, h_)
    if L > 250 and min(w_, h_) < 40:
        cand.append((L, r))
for L, r in sorted(cand, key=lambda t: -t[0])[:25]:
    x0, y0, x1, y1 = r[6]
    print(f"#{r[0]:<5} type={r[1]} fill={r[2]} stroke={r[3]} w={r[4]} L={L:.1f} bbox=({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})")
