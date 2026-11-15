
import bpy
import os
from collections import defaultdict
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

KEEP = {"Deck", "Base", "Ground"}
GAP = 0.006

def meshes():
    return [o for o in bpy.data.objects if o.type == 'MESH' and len(o.data.polygons)]

def tree_verts(o):
    verts = [o.matrix_world @ v.co for v in o.data.vertices]
    return BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in o.data.polygons],
                                all_triangles=False), verts

def box_of(verts):
    return (Vector((min(v.x for v in verts), min(v.y for v in verts), min(v.z for v in verts))),
            Vector((max(v.x for v in verts), max(v.y for v in verts), max(v.z for v in verts))))

def volume(lo, hi):
    s = hi - lo
    return max(1e-5, s.x * s.y * s.z)

def scene_state():
    data = {}
    for o in meshes():
        tree, verts = tree_verts(o)
        lo, hi = box_of(verts)
        data[o.name] = (o, tree, lo, hi)
    return data

def find_pairs(data):
    names = sorted(data)
    out = []
    for i, a in enumerate(names):
        _, ta, la, ha = data[a]
        for b in names[i + 1:]:
            _, tb, lb, hb = data[b]
            if not (la.x <= hb.x and lb.x <= ha.x and la.y <= hb.y and lb.y <= ha.y
                    and la.z <= hb.z and lb.z <= ha.z):
                continue
            if ta.overlap(tb):
                out.append((a, b))
    return out

def report(tag, pairs):
    same = diff = 0
    for a, b in pairs:
        oa, ob = bpy.data.objects[a], bpy.data.objects[b]
        ma = oa.data.materials[0].name if oa.data.materials else "-"
        mb = ob.data.materials[0].name if ob.data.materials else "-"
        same += ma == mb
        diff += ma != mb
    print(tag, "PAIRS", len(pairs), "SAME_MAT", same, "DIFF_MAT", diff)

bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type in {'MESH', 'CURVE'}:
        o.select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects["Deck"]
bpy.ops.object.convert(target='MESH')
print("CONVERTED", len(meshes()))

data = scene_state()
pairs = find_pairs(data)
report("BEFORE", pairs)

for rnd in range(3):
    data = scene_state()
    pairs = find_pairs(data)
    if not pairs:
        break
    trimmed = failed = removed = 0
    dead = set()
    for a, b in pairs:
        if a in dead or b in dead:
            continue
        oa, ob = bpy.data.objects.get(a), bpy.data.objects.get(b)
        if oa is None or ob is None:
            continue
        va = volume(*box_of([oa.matrix_world @ v.co for v in oa.data.vertices]))
        vb = volume(*box_of([ob.matrix_world @ v.co for v in ob.data.vertices]))
        target, cutter = (oa, ob) if va <= vb else (ob, oa)
        if target.name in KEEP:
            failed += 1
            continue
        ok = False
        for grow in (GAP, GAP * 3, GAP * 8):
            lo, hi = box_of([cutter.matrix_world @ v.co for v in cutter.data.vertices])
            centre = (lo + hi) / 2
            size = Vector((max(0.01, hi.x - lo.x), max(0.01, hi.y - lo.y),
                           max(0.01, hi.z - lo.z)))
            dup = cutter.copy()
            dup.data = cutter.data.copy()
            bpy.context.collection.objects.link(dup)
            dup.data.transform(Matrix.Translation(centre)
                               @ Matrix.Diagonal(Vector((1 + grow / size.x,
                                                        1 + grow / size.y,
                                                        1 + grow / size.z, 1)))
                               @ Matrix.Translation(-centre) @ dup.matrix_world)
            dup.matrix_world = Matrix.Identity(4)
            mod = target.modifiers.new("trim", 'BOOLEAN')
            mod.operation = 'DIFFERENCE'
            mod.solver = 'EXACT'
            mod.object = dup
            bpy.context.view_layer.objects.active = target
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except Exception:
                if mod.name in [m.name for m in target.modifiers]:
                    target.modifiers.remove(mod)
            bpy.data.objects.remove(dup, do_unlink=True)
            if len(target.data.vertices) == 0:
                dead.add(target.name)
                bpy.data.objects.remove(target, do_unlink=True)
                ok = True
                removed += 1
                break
            ttree, tverts = tree_verts(target)
            ct, cverts = tree_verts(cutter)
            tlo, thi = box_of(tverts)
            clo, chi = box_of(cverts)
            overlap = (tlo.x <= chi.x and clo.x <= thi.x and tlo.y <= chi.y
                       and clo.y <= thi.y and tlo.z <= chi.z and clo.z <= thi.z)
            if not overlap or not ttree.overlap(ct):
                ok = True
                break
        trimmed += ok
        failed += not ok
    print("ROUND", rnd, "TRIMMED", trimmed, "REMOVED", removed, "FAILED", failed)
    if trimmed == 0:
        break

data = scene_state()
pairs = find_pairs(data)
report("AFTER", pairs)
sizes = defaultdict(int)
for a, b in pairs:
    sizes[(a.split('.')[0], b.split('.')[0])] += 1
for key, n in sorted(sizes.items(), key=lambda kv: -kv[1])[:14]:
    print("  left", key, n)

balls = [o for o in meshes() if o.name.startswith(("Front pit ball", "Grand pit ball", "Room ball"))]
worst = 9.9
for i, a in enumerate(balls):
    for b in balls[i + 1:]:
        d = (a.matrix_world.translation - b.matrix_world.translation).length
        worst = min(worst, d - a.dimensions.x / 2 - b.dimensions.x / 2)
print("BALLS", len(balls), "MIN_GAP %.4f" % worst)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(bpy.data.filepath),
                                                 "bouncy_castle.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(os.path.dirname(bpy.data.filepath),
                                                "bouncy_castle.glb"), export_format="GLB")
print("DONE")
