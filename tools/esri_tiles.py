# -*- coding: utf-8 -*-
"""Download Esri World Imagery tiles and stitch a georeferenced mosaic.

Usage: python esri_tiles.py out.png ZOOM LAT_MIN LON_MIN LAT_MAX LON_MAX [max_tiles]
Writes out.png + out.json with geo transform (px per degree).
"""
import sys, os, math, json, time, urllib.request, io

def deg2num(lat, lon, z):
    n = 2.0 ** z
    x = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2.0 * n
    return x, y

def num2deg(x, y, z):
    n = 2.0 ** z
    lon = x / n * 360.0 - 180.0
    lat_r = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    return math.degrees(lat_r), lon

def main():
    out = sys.argv[1]
    z = int(sys.argv[2])
    lat_min, lon_min, lat_max, lon_max = map(float, sys.argv[3:7])
    max_tiles = int(sys.argv[7]) if len(sys.argv) > 7 else 400
    from PIL import Image
    x0, y0 = deg2num(lat_max, lon_min, z)
    x1, y1 = deg2num(lat_min, lon_max, z)
    tx0, ty0 = int(math.floor(x0)), int(math.floor(y0))
    tx1, ty1 = int(math.floor(x1)), int(math.floor(y1))
    cols, rows = tx1 - tx0 + 1, ty1 - ty0 + 1
    print(f'z={z} tiles {cols}x{rows} = {cols * rows}')
    if cols * rows > max_tiles:
        print('too many tiles, abort'); return
    W, H = cols * 256, rows * 256
    mosaic = Image.new('RGB', (W, H), (20, 20, 20))
    cache = os.path.join(os.path.dirname(out), 'tile_cache')
    os.makedirs(cache, exist_ok=True)
    ok = fail = 0
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            p = os.path.join(cache, f'{z}_{tx}_{ty}.jpg')
            if not os.path.exists(p) or os.path.getsize(p) < 500:
                url = f'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{ty}/{tx}'
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 dsh-scenery/1.0'})
                try:
                    data = urllib.request.urlopen(req, timeout=30).read()
                    open(p, 'wb').write(data)
                    time.sleep(0.05)
                except Exception as e:
                    fail += 1
                    print('fail', tx, ty, e)
                    continue
            try:
                im = Image.open(p).convert('RGB')
                mosaic.paste(im, ((tx - tx0) * 256, (ty - ty0) * 256))
                ok += 1
            except Exception as e:
                fail += 1
                print('bad tile', tx, ty, e)
    mosaic.save(out, quality=92)
    meta = {
        'out': out, 'zoom': z, 'size': [W, H], 'tiles_ok': ok, 'tiles_fail': fail,
        'tile_x0': tx0, 'tile_y0': ty0,
        'nw': num2deg(tx0, ty0, z), 'se': num2deg(tx1 + 1, ty1 + 1, z),
        'm_per_tile_px': 156543.03392 * math.cos(math.radians((lat_min + lat_max) / 2)) / (2 ** z) / 256,
    }
    json.dump(meta, open(os.path.splitext(out)[0] + '.json', 'w'), indent=1)
    print(json.dumps(meta, indent=1))

if __name__ == '__main__':
    main()
