# -*- coding: utf-8 -*-
"""Minimal PDF probe: no external deps. Extract text ops + image XObjects.

Usage: python pdf_probe.py <file.pdf> [outdir]
Writes: <outdir>/<name>_page{N}_text.txt, <outdir>/<name>_img{K}.jpg|.png
Prints a short summary (pages, fonts, images, text length).
"""
import sys, os, re, zlib, json

def find_streams(data):
    out = []
    for m in re.finditer(rb'stream\r?\n', data):
        start = m.end()
        end = data.find(b'endstream', start)
        if end < 0:
            continue
        raw = data[start:end]
        # dict is the bytes between previous '<<' and 'stream'
        head_start = data.rfind(b'<<', max(0, m.start() - 4000), m.start())
        head = data[head_start:m.start()] if head_start >= 0 else b''
        out.append((head, raw, start, end))
    return out

def try_decode(head, raw):
    if b'FlateDecode' in head:
        for trim in (0, 1, 2):
            try:
                d = zlib.decompress(raw[:len(raw) - trim] if trim else raw)
                return d, 'flate'
            except Exception:
                continue
        try:
            d = zlib.decompressobj().decompress(raw)
            return d, 'flate-partial'
        except Exception:
            return None, 'flate-fail'
    return raw, 'raw'

TEXT_OP = re.compile(rb'\((?:[^()\\]|\\.)*\)|<([0-9A-Fa-f\s]+)>')
def extract_text(content):
    """Very rough: pull strings from Tj/TJ operators."""
    chunks = []
    for m in re.finditer(rb'\[(.*?)\]\s*TJ|\((?:[^()\\]|\\.)*\)\s*Tj', content, re.S):
        seg = m.group(0)
        for s in TEXT_OP.finditer(seg):
            g = s.group(0)
            if g.startswith(b'('):
                body = g[1:-1]
                body = re.sub(rb'\\([nrtbf()\\])', lambda mm: {b'n': b'\n', b'r': b'\r', b't': b'\t', b'b': b'\b', b'f': b'\f', b'(': b'(', b')': b')', b'\\': b'\\'}[mm.group(1)], body)
                try:
                    chunks.append(body.decode('latin-1'))
                except Exception:
                    pass
            else:
                hexs = re.sub(rb'\s', b'', s.group(1))
                if len(hexs) % 2:
                    hexs += b'0'
                try:
                    b = bytes.fromhex(hexs.decode())
                except Exception:
                    continue
                # assume 2-byte CID -> try utf-16be
                if len(b) % 2 == 0:
                    try:
                        chunks.append(b.decode('utf-16-be', 'ignore'))
                    except Exception:
                        chunks.append(b.decode('latin-1'))
                else:
                    chunks.append(b.decode('latin-1'))
    return ' '.join(x for x in chunks if x.strip())

def main():
    path = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(path), 'probe')
    os.makedirs(outdir, exist_ok=True)
    data = open(path, 'rb').read()
    name = os.path.splitext(os.path.basename(path))[0]
    streams = find_streams(data)
    summary = {'file': path, 'bytes': len(data), 'streams': len(streams),
               'pages': len(re.findall(rb'/Type\s*/Page[^s]', data)),
               'images_dct': len(re.findall(rb'/DCTDecode', data)),
               'images_flate': len(re.findall(rb'/FlateDecode.*?/Image', data, re.S)),
               'fonts': sorted(set(x.decode('latin-1') for x in re.findall(rb'/BaseFont\s*/([#\w+\-.,]+)', data)))}
    text_all = []
    n_img = 0
    for i, (head, raw, s, e) in enumerate(streams):
        dec, kind = try_decode(head, raw)
        if dec is None:
            continue
        if b'DCTDecode' in head:
            p = os.path.join(outdir, f'{name}_img{n_img}.jpg')
            open(p, 'wb').write(dec)
            n_img += 1
            continue
        if b'/Image' in head and b'/Subtype' in head:
            p = os.path.join(outdir, f'{name}_img{n_img}.bin')
            open(p, 'wb').write(dec)
            n_img += 1
            continue
        # content stream?
        if b'BT' in dec or b'Tj' in dec or b'TJ' in dec:
            t = extract_text(dec)
            if t.strip():
                text_all.append((i, t))
    txt = '\n\n'.join(t for _, t in text_all)
    tp = os.path.join(outdir, f'{name}.text.txt')
    open(tp, 'w', encoding='utf-8', errors='replace').write('\n\n'.join(t for _, t in text_all))
    summary['text_streams'] = len(text_all)
    summary['text_chars'] = len(txt)
    summary['images_saved'] = n_img
    summary['text_path'] = tp
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print('--- first 2500 chars of text ---')
    print(txt[:2500])

if __name__ == '__main__':
    main()
