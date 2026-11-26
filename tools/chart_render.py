# -*- coding: utf-8 -*-
"""Render ICAO chart PDFs to PNG + dump vector drawing stats & words (PyMuPDF)."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pylib'))
import pymupdf

def main():
    src = sys.argv[1]
    outdir = sys.argv[2]
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 150
    os.makedirs(outdir, exist_ok=True)
    doc = pymupdf.open(src)
    info = {'src': src, 'pages': len(doc)}
    for pno, page in enumerate(doc):
        r = page.rect
        zoom = dpi / 72.0
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        p = os.path.join(outdir, f'page{pno + 1}_{dpi}dpi.png')
        pix.save(p)
        dr = page.get_drawings()
        words = page.get_text('words')
        info[pno] = {
            'rect_pt': [r.x0, r.y0, r.x1, r.y1],
            'png': p, 'png_size': [pix.width, pix.height],
            'drawings': len(dr),
            'words': len(words),
            'text': page.get_text('text')[:1500],
        }
        # drawing kinds histogram
        kinds = {}
        for d in dr:
            k = (d.get('type', '?'), d.get('width'), d.get('color') is not None)
            kinds[str(k)] = kinds.get(str(k), 0) + 1
        info[pno]['kinds'] = dict(sorted(kinds.items(), key=lambda kv: -kv[1])[:10])
        json.dump(dr, open(os.path.join(outdir, f'page{pno + 1}_drawings.json'), 'w', encoding='utf-8'), default=str)
        json.dump(words, open(os.path.join(outdir, f'page{pno + 1}_words.json'), 'w', encoding='utf-8'), default=str)
    json.dump(info, open(os.path.join(outdir, 'info.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    print(json.dumps({k: (v if k == 'pages' or k == 'src' else {kk: v[kk] for kk in ('rect_pt', 'png_size', 'drawings', 'words', 'kinds')}) for k, v in info.items()}, ensure_ascii=False, indent=1))

if __name__ == '__main__':
    main()
