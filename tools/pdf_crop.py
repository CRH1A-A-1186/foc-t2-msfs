# -*- coding: utf-8 -*-
"""Render a PDF page region at high DPI. Usage: pdf_crop.py src.pdf out.png x0 y0 x1 y1 [dpi]"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib'))
import pymupdf
src, out = sys.argv[1], sys.argv[2]
x0, y0, x1, y1 = map(float, sys.argv[3:7])
dpi = int(sys.argv[7]) if len(sys.argv) > 7 else 300
doc = pymupdf.open(src)
page = doc[0]
clip = pymupdf.Rect(x0, y0, x1, y1)
zoom = dpi / 72.0
pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
pix.save(out)
print(out, pix.width, pix.height, 'm/px@', dpi, 6.0811 * 72 / dpi)
