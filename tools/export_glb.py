# -*- coding: utf-8 -*-
"""Export GEO-*/MK-* meshes to glTF(.glb) for MSFS and write out/manifest.json.

Run: blender -b build/foc-t2.blend -P tools/export_glb.py
"""
import bpy, os, json, hashlib, math
from mathutils import Vector

ROOT = r"F:\dshproj\foc-t2"
OUT = os.path.join(ROOT, 'out')
os.makedirs(OUT, exist_ok=True)
GLB = os.path.join(OUT, 'foc-t2.glb')

spec = {}
try:
    import importlib.util
    sp = importlib.util.spec_from_file_location('foc_spec', os.path.join(ROOT, 'spec.py'))
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    spec = mod.SPEC
except Exception as e:
    print('spec load failed', e)

objs = [o for o in bpy.data.objects if o.type == 'MESH' and (o.name.startswith('GEO-') or o.name.startswith('MK-'))]
bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]

bpy.ops.export_scene.gltf(
    filepath=GLB,
    export_format='GLB',
    use_selection=True,
    export_yup=True,
    export_apply=True,
    export_materials='EXPORT',
    export_cameras=False,
    export_lights=False,
    export_extras=True,
)

md5 = hashlib.md5(open(GLB, 'rb').read()).hexdigest()
size = os.path.getsize(GLB)

pts = []
for o in objs:
    for c in o.bound_box:
        pts.append(o.matrix_world @ Vector(c))
mn = [round(min(p[i] for p in pts), 2) for i in range(3)]
mx = [round(max(p[i] for p in pts), 2) for i in range(3)]

tri = 0
for o in objs:
    tri += sum(len(p.vertices) - 2 for p in o.data.polygons)

manifest = {
    'asset': 'FOC-T2 (ZSFZ) terminal + taxiways',
    'version': 'r1',
    'built': '2026-11-26',
    'format': 'glTF 2.0 binary (.glb)',
    'units': 'metres (1 unit = 1 m)',
    'axes': {'gltf': 'X = east, Y = up, Z = south (north faces -Z)', 'blender_source': 'X east, Y north, Z up'},
    'origin': {'lat': spec.get('origin', {}).get('lat', 25.929254),
               'lon': spec.get('origin', {}).get('lon', 119.672524),
               'elev_m': spec.get('origin', {}).get('elev_m', 14.0),
               'note': 'local ENU origin = ZSFZ aerodrome reference point; place model at this lat/lon in MSFS'},
    'bbox_blender_m': {'min': mn, 'max': mx,
                       'size': [round(mx[i] - mn[i], 2) for i in range(3)]},
    'objects': len(objs),
    'tris': tri,
    'glb': {'path': GLB, 'bytes': size, 'md5': md5},
    'contents': {
        'terminal': ['GEO-T2-podium', 'GEO-T2-glass', 'GEO-T2-roof'],
        'runways': 'GEO-RWY-0/1 (80 m paved width = 45 m runway + 2x17.5 m shoulders)',
        'taxiways': 'GEO-TWY-0/1 (23 m wide ribbons, OSM centre lines)',
        'aprons': 'GEO-APRON-0..4 (OSM apron polygons)',
        'markings': 'MK-TWY-CL-000..063 (0.45 m yellow centre lines)',
    },
    'sources': [
        'CAAC AIP ZSFZ aircraft parking chart 2P-1 (AIRAC AMDT 11/26, EFF 2026-10-28) — T2 footprint, runway/taxiway layout, scale',
        'OpenStreetMap via Overpass API (2026-07-28 snapshot) — taxiway centre lines, apron polygons, runway axes, T2 polygon cross-check (ODbL)',
        'OurAirports runways.csv — ZSFZ runway ends, lengths 3600 m, widths 45 m',
        'Public reports — T2 GFA ~255,000 m2, height 39.7 m, opened 2026-09-16; RWY04/22 named by CAAC though roughly parallel to 03/21',
    ],
    'limitations': [
        'T2 exterior is a massing model: saddle roof (马鞍墙 arc) not modelled yet - r1 has a flat ridge; no facade mullions, no jet bridges, no roof skylight band.',
        'T2 footprint comes from the AIP chart vector (718 x 900 m bbox, 182,990 m2); chart is to scale (runway separation check: chart 1923 m vs OSM 1920-1926 m).',
        'T1 terminal, cargo buildings, GTC, control tower, stands markings and lighting are NOT included (out of scope r1).',
        'Taxiway widths are uniform 23 m (ICAO code E/F); OSM has no width tags, chart gives no per-taxiway width.',
        'Runway 04/22 drawn parallel to 03/21 at 1923 m separation (chart + OSM + press reports agree); THR04 displaced 200 m is not modelled separately.',
        'Ground is flat at z=0 (ARP elevation 14.0 m is NOT applied); MSFS terrain/altitude handling must offset the model.',
        'No LODs, no collision mesh, no PBR textures (materials are flat colours).',
    ],
}
json.dump(manifest, open(os.path.join(OUT, 'manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('EXPORT ' + json.dumps({'glb': GLB, 'bytes': size, 'md5': md5, 'objects': len(objs), 'tris': tri,
                             'size_m': manifest['bbox_blender_m']['size']}, ensure_ascii=False))
