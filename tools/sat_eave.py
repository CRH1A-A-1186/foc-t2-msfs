"""r7 / step 1 - georeference the new ZSFZ T2 satellite capture and re-vectorise the roof eave.

Why: the r6 footprint came from the CAAC AIP 2P-1 chart (calibrated on runway spacing). A newer
z18 capture (finished roof, jet bridges, apron) shows the real eave sits a few metres away and
the chart outline is slightly fat. This tool snaps the r6 ring onto the real edge and writes a
clean closed polygon in the same ENU frame as build/geo.json.

    python tools/sat_eave.py [image] [--out build/t2_eave_sat.json]

The reference image is NOT redistributable and is not part of the repository; only the derived
ring (build/t2_eave_sat.json) is committed.

Pipeline
    1. rough roof mask  : colour cast (B-R) + brightness window, closing, largest component
    2. similarity fit   : scale from the min-area rectangle, rotation/translation by IoU
    3. edge snap        : each resampled ring vertex moves along its normal to the strongest
                          luminance / colour-cast gradient within +-45 px, offsets median-smoothed
    4. cleanup          : self-intersection loops removed, <1.5 m points merged, RDP 2.5 m,
                          orientation normalised to CW (same as build/geo.json)
"""
import argparse
import collections
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_IMG = os.path.join(ROOT, "ref", "sat", "new", "t2_z18_2026.png")
DEFAULT_OUT = os.path.join(ROOT, "build", "t2_eave_sat.json")
GEO = os.path.join(ROOT, "build", "geo.json")


# ------------------------------------------------------------------ morphology
def dilate(m, r):
    o = m.copy()
    for _ in range(r):
        d = o.copy()
        d[1:, :] |= o[:-1, :]
        d[:-1, :] |= o[1:, :]
        d[:, 1:] |= o[:, :-1]
        d[:, :-1] |= o[:, 1:]
        o = d
    return o


def erode(m, r):
    o = m.copy()
    for _ in range(r):
        d = o.copy()
        d[1:, :] &= o[:-1, :]
        d[:-1, :] &= o[1:, :]
        d[:, 1:] &= o[:, :-1]
        d[:, :-1] &= o[:, 1:]
        o = d
    return o


def largest_component(m, block=4):
    H, W = m.shape
    h, w = H // block, W // block
    m4 = m[:h * block, :w * block].reshape(h, block, w, block).any(axis=(1, 3))
    lab = np.zeros((h, w), np.int32)
    cur = best = 0
    best_n = -1
    for y0 in range(h):
        for x0 in range(w):
            if m4[y0, x0] and lab[y0, x0] == 0:
                cur += 1
                n = 0
                dq = collections.deque([(y0, x0)])
                lab[y0, x0] = cur
                while dq:
                    y, x = dq.popleft()
                    n += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and m4[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = cur
                            dq.append((ny, nx))
                if n > best_n:
                    best_n, best = n, cur
    out = np.zeros((H, W), bool)
    out[:h * block, :w * block] = np.repeat(np.repeat(lab == best, block, 0), block, 1)
    return out & m


def fill_holes(m):
    H, W = m.shape
    inv = ~m
    seen = np.zeros((H, W), bool)
    dq = collections.deque()
    border = ([(0, x) for x in range(W)] + [(H - 1, x) for x in range(W)] +
              [(y, 0) for y in range(H)] + [(y, W - 1) for y in range(H)])
    for y, x in border:
        if inv[y, x] and not seen[y, x]:
            seen[y, x] = True
            dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and inv[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                dq.append((ny, nx))
    return m | (inv & ~seen)


# ------------------------------------------------------------------ geometry
def ring_yup(p_enu, s, th, t, H):
    c, sn = math.cos(th), math.sin(th)
    R = np.array([[c, -sn], [sn, c]])
    q = (p_enu @ R.T) * s + t
    return np.stack([q[:, 0], (H - 1) - q[:, 1]], 1)


def ring_enu(p_px, s, th, t, H):
    c, sn = math.cos(-th), math.sin(-th)
    R = np.array([[c, -sn], [sn, c]])
    q = np.stack([p_px[:, 0], (H - 1) - p_px[:, 1]], 1)
    return ((q - t) @ R.T) / s


def raster(ring_px, W, H):
    img = Image.new("1", (W, H), 0)
    ImageDraw.Draw(img).polygon([(float(u), float(v)) for u, v in ring_px], fill=1)
    return np.asarray(img, bool)


def iou(a, b):
    u = (a | b).sum()
    return float((a & b).sum() / u) if u else 0.0


def minrect(P):
    def hull(p):
        p = p[np.lexsort((p[:, 1], p[:, 0]))]

        def half(pp):
            h = []
            for q in pp:
                while len(h) >= 2:
                    a, b = h[-1], h[-2]
                    if (a[0] - b[0]) * (q[1] - b[1]) - (a[1] - b[1]) * (q[0] - b[0]) <= 0:
                        h.pop()
                    else:
                        break
                h.append(q)
            return h
        return np.array(half(p)[:-1] + half(p[::-1])[:-1])
    h = hull(P)
    best = None
    for i in range(len(h)):
        e = h[(i + 1) % len(h)] - h[i]
        th = math.atan2(e[1], e[0])
        c, s = math.cos(-th), math.sin(-th)
        Rm = np.array([[c, -s], [s, c]])
        q = h @ Rm.T
        w, hh = q[:, 0].max() - q[:, 0].min(), q[:, 1].max() - q[:, 1].min()
        if best is None or w * hh < best[0]:
            ctr = np.array([(q[:, 0].max() + q[:, 0].min()) / 2, (q[:, 1].max() + q[:, 1].min()) / 2])
            best = (w * hh, w, hh, th, ctr @ Rm)
    return best


def signed_area(r):
    x, y = r[:, 0], r[:, 1]
    return 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def resample_ring(r, step):
    rr = np.vstack([r, r[:1]])
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(rr, axis=0).T))]
    n = max(int(d[-1] / step), 8)
    out = []
    for kk in np.linspace(0, d[-1], n, endpoint=False):
        i = min(max(int(np.searchsorted(d, kk)) - 1, 0), len(r) - 1)
        seg = d[i + 1] - d[i] if i + 1 < len(d) else 1.0
        f = (kk - d[i]) / seg if seg else 0.0
        out.append(r[i] + (r[(i + 1) % len(r)] - r[i]) * f)
    return np.array(out)


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    n = math.hypot(*ab)
    if n == 0:
        d = np.hypot(*(pts - a).T)
    else:
        rel = pts - a
        d = np.abs(ab[0] * rel[:, 1] - ab[1] * rel[:, 0]) / n
    i = int(np.argmax(d))
    if d[i] > eps:
        return np.vstack([rdp(pts[:i + 1], eps)[:-1], rdp(pts[i:], eps)])
    return np.array([a, b])


def _seg_int(a, b, c, d):
    def cr(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    d1, d2, d3, d4 = cr(c, d, a), cr(c, d, b), cr(a, b, c), cr(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def crossings(r):
    n = len(r)
    out = []
    for i in range(n):
        for j in range(i + 2, n):
            if (j + 1) % n == i:
                continue
            if _seg_int(r[i], r[(i + 1) % n], r[j], r[(j + 1) % n]):
                out.append((i, j))
    return out


def clean_ring(r, min_seg=1.5, max_iter=40):
    """Remove self-intersection loops, merge tiny segments, force CW (build/geo.json convention)."""
    for _ in range(max_iter):
        c = crossings(r)
        if not c:
            break
        i, j = c[0]
        n = len(r)
        if (j - i) < (n - (j - i)):
            r = np.delete(r, [k % n for k in range(i + 1, j + 1)], axis=0)
        else:
            r = np.delete(r, [k % n for k in list(range(0, i + 1)) + list(range(j + 1, n))], axis=0)
    for _ in range(50):
        d = np.hypot(*np.diff(np.vstack([r, r[:1]]), axis=0).T)
        k = int(np.argmin(d))
        if d[k] >= min_seg:
            break
        r = np.delete(r, (k + 1) % len(r), axis=0)
    if signed_area(r) > 0:
        r = r[::-1]
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", default=DEFAULT_IMG)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--geo", default=GEO)
    args = ap.parse_args()

    im = Image.open(args.image).convert("RGB")
    W, H = im.size
    a = np.asarray(im.filter(ImageFilter.MedianFilter(3))).astype(np.float32)
    Rc, Gc, Bc = a[..., 0], a[..., 1], a[..., 2]
    V = a.max(axis=2)
    L = 0.299 * Rc + 0.587 * Gc + 0.114 * Bc
    gy, gx = np.gradient(L)
    E = np.hypot(gx, gy)
    gy2, gx2 = np.gradient(Bc - Rc)
    E = E + 0.8 * np.hypot(gx2, gy2)
    E = np.asarray(Image.fromarray((np.clip(E, 0, 60) * 4).astype(np.uint8), "L")
                   .filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 4.0

    geo = json.load(open(args.geo, encoding="utf-8"))
    aip = np.array(geo["t2"]["ring"], float)

    # ---- 1/2. rough mask + similarity fit
    core = ((Bc - Rc) >= 1) & (V >= 176) & (V <= 221)
    mA = fill_holes(largest_component(erode(dilate(core, 8), 8)))
    ys, xs = np.nonzero(mA)
    ip = np.stack([xs, ys], 1).astype(float)
    ip[:, 1] = (H - 1) - ip[:, 1]
    _, wi, hi, thi, ci = minrect(ip)
    _, wm, hm, thm, cm = minrect(aip)
    s = max(wi, hi) / max(wm, hm)
    th = thm - thi
    Rm = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    t = ci - (aip @ Rm.T).mean(0) * s

    def score(s2, th2, t2):
        return iou(raster(ring_yup(aip, s2, th2, t2, H), W, H), mA)

    v = score(s, th, t)
    for st_th, st_t in ((2.0, 20.0), (0.7, 8.0), (0.25, 3.0)):
        improved = True
        while improved:
            improved = False
            for dth in (st_th, -st_th, 0):
                for dx, dy in ((0, 0), (st_t, 0), (-st_t, 0), (0, st_t), (0, -st_t)):
                    th2 = th + math.radians(dth)
                    t2 = t + np.array([dx, dy], float)
                    v2 = score(s, th2, t2)
                    if v2 > v + 1e-6:
                        v, th, t, improved = v2, th2, t2, True
    for ds in (0.02, -0.02, 0.008, -0.008, 0.003, -0.003):
        s2 = s * (1 + ds)
        v2 = score(s2, th, t)
        if v2 > v + 1e-6:
            v, s = v2, s2
    print(f"fit  {1/s:.4f} m/px  rot {math.degrees(th):.2f} deg  IoU(ring vs mask) {v:.4f}")

    # ---- 3. snap to the real eave edge
    dense = resample_ring(aip, 4.0)
    px = ring_yup(dense, s, th, t, H)
    tg = np.roll(px, -1, 0) - np.roll(px, 1, 0)
    tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
    nrm = np.stack([-tg[:, 1], tg[:, 0]], 1)
    search = 45
    off = np.zeros(len(dense))
    for i in range(len(dense)):
        bestv, besto = -1.0, 0.0
        for d in range(-search, search + 1):
            xi = int(round(px[i, 0] + nrm[i, 0] * d))
            yi = int(round(px[i, 1] + nrm[i, 1] * d))
            if not (2 <= xi < W - 2 and 2 <= yi < H - 2):
                continue
            val = E[yi, xi] - 0.02 * abs(d)
            if val > bestv:
                bestv, besto = val, d
        off[i] = besto
    kern = np.ones(13) / 13
    off = np.convolve(np.r_[off[-6:], off, off[:6]], kern, mode="same")[6:-6]
    enu = ring_enu(px + nrm * off[:, None], s, th, t, H)
    ring = clean_ring(rdp(np.vstack([enu, enu[:1]]), 2.5)[:-1])
    print(f"ring {len(ring)} verts  area {abs(signed_area(ring)):.0f} m2  "
          f"(AIP {abs(signed_area(aip)):.0f} m2, ratio {abs(signed_area(ring))/abs(signed_area(aip)):.3f})  "
          f"self-intersections {len(crossings(ring))}")

    A = resample_ring(ring, 3.0)
    B = resample_ring(aip, 3.0)
    d1 = np.array([np.min(np.hypot(*(B - p).T)) for p in A])
    d2 = np.array([np.min(np.hypot(*(A - p).T)) for p in B])
    print(f"ring->AIP mean {d1.mean():.2f} max {d1.max():.2f} m | AIP->ring mean {d2.mean():.2f} max {d2.max():.2f} m")

    json.dump({
        "what": "T2 roof eave outline snapped onto the real edge in a new z18 satellite capture; ENU metres, same frame as build/geo.json",
        "source": "local satellite capture - the image is NOT redistributable and is not part of this repository",
        "tool": "tools/sat_eave.py",
        "method": "colour mask -> similarity fit (scale from the min-area rectangle, rotation/translation by IoU) -> per-vertex normal edge search (+-45 px) -> offset smoothing -> loop removal + RDP 2.5 m + CW orientation",
        "fit": {
            "m_per_px": round(1 / s, 5),
            "rotation_deg": round(math.degrees(th), 4),
            "translation_px_yup": [round(float(t[0]), 2), round(float(t[1]), 2)],
            "iou_ring_vs_mask": round(v, 4),
            "scale_anchor": "envelope long side matched to the r6 AIP footprint (924.3 m); absolute scale about +-5 %",
            "edge_search_px": search,
        },
        "stats": {
            "verts": int(len(ring)),
            "area_m2": round(float(abs(signed_area(ring))), 1),
            "aip_area_m2": round(float(abs(signed_area(aip))), 1),
            "area_ratio": round(float(abs(signed_area(ring)) / abs(signed_area(aip))), 4),
            "dist_ring_to_aip_m": {"mean": round(float(d1.mean()), 2),
                                   "p95": round(float(np.percentile(d1, 95)), 2),
                                   "max": round(float(d1.max()), 2)},
            "dist_aip_to_ring_m": {"mean": round(float(d2.mean()), 2),
                                   "p95": round(float(np.percentile(d2, 95)), 2),
                                   "max": round(float(d2.max()), 2)},
            "self_intersections": len(crossings(ring)),
            "orientation": "CW",
        },
        "ring_enu_m": [[round(float(u), 2), round(float(w), 2)] for u, w in ring],
    }, open(args.out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("wrote", args.out)


if __name__ == "__main__":
    main()
