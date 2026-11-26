# -*- coding: utf-8 -*-
"""Crop a georeferenced mosaic by lat/lon bbox. Usage: sat_crop.py mosaic.png out.png lat_min lon_min lat_max lon_max [scale]"""
import sys, os, json, math
from PIL import Image

def deg2num(lat, lon, z):
    n = 2.0 ** z
    x = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2.0 * n
    return x, y

def main():
    src, out = sys.argv[1], sys.argv[2]
    lat_min, lon_min, lat_max, lon_max = map(float, sys.argv[3:7])
    scale = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
    meta = json.load(open(os.path.splitext(src)[0] + '.json'))
    z = meta['zoom']
    im = Image.open(src)
    x0, y0 = deg2num(lat_max, lon_min, z)
    x1, y1 = deg2num(lat_min, lon_max, z)
    px0 = (x0 - meta['tile_x0']) * 256
    py0 = (y0 - meta['tile_y0']) * 256
    px1 = (x1 - meta['tile_x0']) * 256
    py1 = (y1 - meta['tile_y0']) * 256
    box = (max(0, int(px0)), max(0, int(py0)), min(im.width, int(px1)), min(im.height, int(py1)))
    crop = im.crop(box)
    if scale != 1.0:
        crop = crop.resize((int(crop.width * scale), int(crop.height * scale)), Image.LANCZOS)
    crop.save(out)
    mpdeg = 111320.0 * math.cos(math.radians((lat_min + lat_max) / 2))
    print(json.dumps({'out': out, 'box_px': box, 'size': crop.size,
                      'm_per_px': 156543.03392 * math.cos(math.radians((lat_min + lat_max) / 2)) / (2 ** z),
                      'crop_m': [(box[2] - box[0]) * 156543.03392 * math.cos(math.radians((lat_min + lat_max) / 2)) / (2 ** z),
                                 (box[3] - box[1]) * 156543.03392 * math.cos(math.radians((lat_min + lat_max) / 2)) / (2 ** z)]}, indent=1))

if __name__ == '__main__':
    main()
