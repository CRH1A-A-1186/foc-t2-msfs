# -*- coding: utf-8 -*-
"""Driver: run the geo + roof geometry builders under Blender's bundled Python (3.12,
which is what tools/pylib/shapely-2.2.0-cp312 was built for).

Run: blender -b -P tools/run_geo_roof.py
"""
import os, runpy, sys
base = os.path.dirname(os.path.abspath(__file__))
for _d in ('pylib', 'pylib313'):
    sys.path.insert(0, os.path.join(base, _d))
print('PY', sys.version.split()[0])
for name in ('build_geo.py', 'build_roof.py'):
    print('== ' + name)
    runpy.run_path(os.path.join(base, name), run_name='__main__')
print('DONE')
