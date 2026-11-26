# -*- coding: utf-8 -*-
"""Repair a PDF via pypdf clone, then render with PyMuPDF."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib'))
from pypdf import PdfReader, PdfWriter
import pymupdf

src = sys.argv[1]
outdir = sys.argv[2]
dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 150
os.makedirs(outdir, exist_ok=True)
base = os.path.splitext(os.path.basename(src))[0][:8]
fixed = os.path.join(outdir, base + '_fixed.pdf')
try:
    r = PdfReader(src)
    print('pypdf pages', len(r.pages))
    w = PdfWriter()
    for p in r.pages:
        w.add_page(p)
    with open(fixed, 'wb') as f:
        w.write(f)
    print('wrote', fixed, os.path.getsize(fixed))
except Exception as e:
    print('pypdf FAIL', type(e).__name__, e)
    fixed = src
doc = pymupdf.open(fixed)
print('mupdf pages', len(doc))
zoom = dpi / 72.0
for i, page in enumerate(doc):
    print(' page', i, page.rect, 'drawings', len(page.get_drawings()))
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    p = os.path.join(outdir, f'ad_page{i + 1}.png')
    pix.save(p)
    print('  ->', p, pix.width, pix.height)
    open(os.path.join(outdir, f'ad_page{i + 1}.txt'), 'w', encoding='utf-8').write(page.get_text('text'))
