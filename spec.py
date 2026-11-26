# -*- coding: utf-8 -*-
"""FOC-T2 spec (frozen 2026-11-26). All builders read constants from here.

Units: 1 Blender unit = 1 m. Airport reference point (ARP) = world origin.
Axes:  +X = east, +Y = north, +Z = up (Blender). glTF export gives MSFS convention
       (X = east, Y = up, Z = south).
"""

SPEC = {
    'project': 'ZSFZ / FOC — Fuzhou Changle Intl, T2 terminal + taxiways (MSFS 2024 scenery)',
    'revision': 'r6 2026-11-26 (thin-plate roof; MSFS export deferred to r7)',
    'units': {'length': 'm', 'scale_length': 1.0, 'coordinate': 'ENU metric, ARP origin'},
    'origin': {'lat': 25.929254, 'lon': 119.672524, 'elev_m': 14.0,
               'source': 'OurAirports ZSFZ ARP row (elev 46 ft)'},

    'runways': [
        {'id': 'RWY03/21', 'length_m': 3600, 'width_m': 45, 'surface': 'CONC',
         'brg_true_deg': 26.8, 'thr03': [25.920435, 119.655359], 'thr21': [25.949340, 119.671631],
         'note': 'existing west runway (03/21), 4F'},
        {'id': 'RWY04/22', 'length_m': 3600, 'width_m': 45, 'surface': 'CONC',
         'brg_true_deg': 26.8, 'thr04': [25.911705, 119.671936], 'thr22': [25.940653, 119.688255],
         'note': 'new east runway, numbered 04/22 by CAAC despite being roughly parallel; '
                 'THR04 displaced 200 m inwards (chart note)', 'parallel_sep_m': 1923},
    ],

    'taxiway': {'width_m': 23.0, 'shoulder_m': 0.0,
                'note': 'ICAO Code E/F straight width; all taxiways modelled 23 m'},

    't2': {
        'name': 'T2 TML', 'height_m': 39.7, 'gfa_m2': 255000,
        'footprint_m2': 182990, 'bbox_m': [718, 900],
        'levels_m': [0, 12, 26, 39.7],   # podium top, glass top, roof crown
        # r6: constant-thickness curved plate (see tools/build_roof.py). The old
        # "saddle loft + flat bottom cap" wedge (14 m thick in section) is gone.
        'roof': {'type': 'thin curved plate, constant thickness',
                 'thickness_m': 1.40,
                 'top_eave_m': 27.35, 'soffit_eave_m': 25.95,
                 'crown_m': 39.70, 'rise_hall_m': 12.35, 'rise_pier_m': 5.50,
                 'tip_uplift_m': 3.00, 'flat_soffit_band_m': 12.0,
                 'eave_overhang_m': 8.0,          # +5 m outline offset + 3 m glass inset
                 'glass_inset_m': 3.0,
                 'grid_step_m': 7.0, 'smooth_iters': 12,
                 'plan_area_m2': 197931},
        'source': 'CAAC 2P-1 chart vector footprint + public reports (GFA/height/opening 2026-09-16)',
    },

    'parts': ['GEO-T2-podium', 'GEO-T2-glass', 'GEO-T2-roof',
              'GEO-RWY-03-21', 'GEO-RWY-04-22',
              'GEO-TWY-pavement', 'GEO-APRON', 'GEO-GROUND',
              'MK-TWY-centrelines'],

    'interfaces': [
        {'a': 'GEO-T2-podium', 'b': 'GEO-APRON', 'interface': 'terminal kerb on apron',
         'nominal_gap_m': 0.0, 'allow_overlap_mm': 300,
         'note': 'podium base sinks 0.3 m into ground slab so no visible gap'},
    ],

    'gates': {
        'audit_mesh': {'state': 'pass', 'boundary_edges': 0, 'nonmanifold_edges': 0,
                       'allow_degenerate': 0},
        'audit_measure': {'t2_height_mm': [39000, 40400], 'rwy_length_mm': [3590000, 3610000]},
        'asm_gate': {'floaters': 0},
    },

    'forbidden': ['no boolean on T2 shell', 'no decimation below 1 m features',
                  'no texture baking in r1', 'no T1 terminal (out of scope)'],

    'delivery': {'formats': ['glb'], 'origin': 'ARP', 'y_up': True,
                 'axis_note': 'glTF: X east, Y up, Z south => model north faces -Z'},
}

if __name__ == '__main__':
    import json
    print(json.dumps(SPEC, ensure_ascii=False, indent=1))
