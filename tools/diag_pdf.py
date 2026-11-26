# -*- coding: utf-8 -*-
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib'))
import pymupdf

SRC = [
    r"F:\Downloads\dd8bec7b-3981-41a3-afd9-e83030989a5c-4399d1e0-dcf2-44d1-9a09-dbfd13ff23ad.pdf",
    r"F:\Downloads\dd9bd161-583e-43ed-b7fe-87beb64df06f-59e0d1f2-72c6-4710-8045-0e5dccf49e12.pdf",
]
for src in SRC:
    try:
        doc = pymupdf.open(src)
        print(os.path.basename(src)[:12], "pages=", len(doc), "repair=", getattr(doc, "is_repaired", None))
        for i, pg in enumerate(doc):
            print("  page", i, pg.rect, "drawings", len(pg.get_drawings()), "words", len(pg.get_text("words")))
    except Exception as e:
        print("FAIL", os.path.basename(src)[:12], type(e).__name__, e)
