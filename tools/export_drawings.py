# -*- coding: utf-8 -*-
"""Export chart vector drawings to clean JSON (points as [x,y])."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib'))
import pymupdf

src = sys.argv[1]
out = sys.argv[2]
doc = pymupdf.open(src)
page = doc[0]
dr = page.get_drawings()
res = []
for d in dr:
    items = []
    for it in d.get('items') or []:
        t = it[0]
        if t == 'l':
            items.append(['l', [it[1].x, it[1].y], [it[2].x, it[2].y]])
        elif t == 'c':
            items.append(['c', [it[1].x, it[1].y], [it[2].x, it[2].y], [it[3].x, it[3].y], [it[4].x, it[4].y]])
        elif t == 're':
            r = it[1]
            items.append(['re', [r.x0, r.y0, r.x1, r.y1]])
        elif t == 'qu':
            q = it[1]
            items.append(['qu', [q.ul.x, q.ul.y], [q.ur.x, q.ur.y], [q.ll.x, q.ll.y], [q.lr.x, q.lr.y]])
    res.append({
        'type': d.get('type'),
        'fill': list(d['fill']) if d.get('fill') else None,
        'color': list(d['color']) if d.get('color') else None,
        'width': d.get('width'),
        'closePath': d.get('closePath'),
        'rect': [d['rect'].x0, d['rect'].y0, d['rect'].x1, d['rect'].y1] if d.get('rect') else None,
        'items': items,
    })
json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
print('drawings', len(res), '->', out, os.path.getsize(out), 'bytes')
