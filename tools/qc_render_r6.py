# -*- coding: utf-8 -*-
"""Render the 5 QC cameras that are saved in build/foc-t2.blend.

Run: blender -b build/foc-t2.blend -P tools/qc_render_r6.py
Out: out/renders/r6_cam-{iso,section,land,eave,top}.png  (1280x720, EEVEE)
"""
import bpy, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'out', 'renders')
os.makedirs(OUT, exist_ok=True)

sc = bpy.context.scene
sc.render.image_settings.file_format = 'PNG'
sc.render.resolution_percentage = 100
try:
    sc.eevee.taa_render_samples = 48
except Exception as e:
    print('samples: %s' % e)

for name in ('CAM-iso', 'CAM-section', 'CAM-land', 'CAM-eave', 'CAM-top'):
    cam = bpy.data.objects.get(name)
    if cam is None:
        print('MISSING', name)
        continue
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.render.filepath = os.path.join(OUT, 'r6_' + name.lower() + '.png')
    bpy.ops.render.render(write_still=True)
    print('SHOT', name, os.path.getsize(sc.render.filepath))
print('RENDER DONE')
