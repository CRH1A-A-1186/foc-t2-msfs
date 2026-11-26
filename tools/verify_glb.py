# -*- coding: utf-8 -*-
"""Re-import the exported GLB in a clean Blender and verify size/orientation/materials."""
import bpy, json, os, math
import os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB = os.path.join(ROOT, 'out', 'foc-t2.glb')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
pts = []
for o in meshes:
    for c in o.bound_box:
        pts.append(o.matrix_world @ Vector(c))
mn = [round(min(p[i] for p in pts), 2) for i in range(3)]
mx = [round(max(p[i] for p in pts), 2) for i in range(3)]
tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in meshes)
mats = sorted({m.name for o in meshes for m in o.data.materials if m})
roots = [o.name for o in bpy.data.objects if o.parent is None]
res = {
    'imported_objects': len(meshes),
    'tris': tris,
    'bbox_min': mn, 'bbox_max': mx,
    'size': [round(mx[i] - mn[i], 2) for i in range(3)],
    'materials': mats,
    'root_objects': roots[:6],
    'root_rotation_euler_deg': [[round(math.degrees(a), 1) for a in o.rotation_euler] for o in bpy.data.objects if o.parent is None][:3],
}
ok = (abs(res['size'][0] - 3361.31) < 1 and abs(res['size'][1] - 4440.41) < 1 and abs(res['size'][2] - 40.0) < 1)
res['dims_match_blend'] = ok
json.dump(res, open(os.path.join(ROOT, 'out', 'verify_glb.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('VERIFY ' + json.dumps(res, ensure_ascii=False))
