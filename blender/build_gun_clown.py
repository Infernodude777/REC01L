import bpy
import math
import os
import random
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def make_mat(name, rgb, rough=0.4, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 0.12
        b.inputs["Coat Roughness"].default_value = 0.25
    return m

M = {
    "skin": make_mat("Skin White", (0.94, 0.91, 0.87), 0.38),
    "white": make_mat("White", (0.97, 0.97, 0.96), 0.32),
    "red": make_mat("Nose Red", (0.78, 0.03, 0.04), 0.30),
    "pink": make_mat("Cheek Pink", (0.95, 0.38, 0.44), 0.42),
    "green": make_mat("Suit Green", (0.05, 0.30, 0.13), 0.36),
    "lime": make_mat("Lime", (0.62, 0.80, 0.06), 0.36),
    "magenta": make_mat("Hair Magenta", (0.60, 0.04, 0.50), 0.44),
    "yellow": make_mat("Hat Yellow", (0.96, 0.66, 0.03), 0.36),
    "leather": make_mat("Strap Leather", (0.13, 0.08, 0.06), 0.58),
    "brass": make_mat("Brass", (0.72, 0.55, 0.16), 0.30, 1.0),
    "black": make_mat("Black", (0.012, 0.012, 0.014), 0.24),
    "dark": make_mat("Mouth Dark", (0.13, 0.005, 0.015), 0.55),
    "ground": make_mat("Studio Floor", (0.88, 0.87, 0.86), 0.9),
}

HEAD_C = Vector((0, 0, 3.22))
HEAD_R = Vector((0.9384, 0.9016, 1.012))

def face_y(x, z):
    t = 1.0 - (x / HEAD_R.x) ** 2 - ((z - HEAD_C.z) / HEAD_R.z) ** 2
    return -HEAD_R.y * math.sqrt(max(0.0, t))

def smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True

def sphere(name, loc, r, material, segs=48, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs,
                                         ring_count=max(8, segs // 2),
                                         radius=r, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = rot
    ob.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    ob.data.materials.append(material)
    smooth(ob)
    return ob

def box(name, loc, size, material, bevel=0.05, segs=3, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(material)
    if bevel > 0:
        b = ob.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = segs
    smooth(ob)
    return ob

def cyl(name, loc, r, depth, material, rot=(0, 0, 0), verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth,
                                        location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(material)
    smooth(ob)
    return ob

def cone(name, loc, r1, r2, depth, material, rot=(0, 0, 0), verts=48):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=depth, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(material)
    smooth(ob)
    return ob

def torus(name, loc, major, minor, material, rot=(0, 0, 0), scale=(1, 1, 1),
          mseg=48, nseg=14):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=mseg, minor_segments=nseg,
                                     location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler = rot
    ob.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    ob.data.materials.append(material)
    smooth(ob)
    return ob

def bar(name, p1, p2, r, material, verts=24):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r,
                                        depth=d.length,
                                        location=(p1 + p2) / 2)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Z", "Y")
    ob.data.materials.append(material)
    smooth(ob)
    return ob

def slab(name, p1, p2, width, thick, material):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cube_add(size=1, location=(p1 + p2) / 2)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (width, thick, d.length)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Z", "Y")
    ob.data.materials.append(material)
    b = ob.modifiers.new("Bevel", "BEVEL")
    b.width = min(width, thick) * 0.35
    b.segments = 2
    smooth(ob)
    return ob

def curve_tube(name, pts, tube, material, cyclic=False):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, co in zip(sp.bezier_points, pts):
        bp.co = co
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    sp.use_cyclic_u = cyclic
    cu.bevel_depth = tube
    cu.bevel_resolution = 5
    cu.use_fill_caps = True
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    ob.data.materials.append(material)
    return ob

sphere("Head", HEAD_C, 0.92, M["skin"], segs=64, scale=(1.02, 0.98, 1.10))
cyl("Neck", (0, 0, 2.22), 0.20, 0.46, M["skin"])

for sx in (-1, 1):
    sphere("Cheek", (sx * 0.54, -0.66, 3.02), 0.215, M["pink"], segs=40,
           scale=(1.0, 0.52, 0.82))

for sx in (-1, 1):
    sphere("Eye", (sx * 0.32, -0.78, 3.52), 0.205, M["white"], segs=48,
           scale=(1.0, 0.72, 1.16))
    sphere("Pupil", (sx * 0.32, -0.895, 3.51), 0.088, M["black"], segs=32,
           scale=(1.0, 0.52, 1.15))
    sphere("Eye glint", (sx * 0.29, -0.94, 3.57), 0.032, M["white"], segs=20)

for sx in (-1, 1):
    inner = Vector((sx * 0.14, 0, 3.74))
    outer = Vector((sx * 0.50, 0, 3.88))
    for t in (0.0, 0.5, 1.0):
        p = inner.lerp(outer, t)
        sphere("Brow", (p.x, face_y(p.x, p.z) + 0.020, p.z), 0.088,
               M["black"], segs=24, scale=(1.45, 0.80, 0.85))

sphere("Nose", (0, -0.96, 3.20), 0.19, M["red"], segs=48,
       scale=(1.05, 1.0, 0.95))
sphere("Nose glint", (0.06, -1.14, 3.27), 0.033, M["white"], segs=20)

lip_pts = [
    (-0.47, -0.780, 2.82), (-0.28, -0.845, 2.90), (0.0, -0.862, 2.92),
    (0.28, -0.845, 2.90), (0.47, -0.780, 2.82), (0.33, -0.790, 2.58),
    (0.0, -0.835, 2.48), (-0.33, -0.790, 2.58),
]
curve_tube("Lips", lip_pts, 0.062, M["red"], cyclic=True)
sphere("Mouth", (0, -0.805, 2.70), 1.0, M["dark"], segs=40,
       scale=(0.38, 0.10, 0.17))

for i in range(7):
    dx = -0.30 + i * 0.10
    dz = 2.79 - 0.04 * abs(i - 3)
    cone("Tooth", (dx, -0.845, dz), 0.052, 0.0, 0.16, M["white"],
         rot=(math.pi, 0, 0), verts=8)
for i in range(5):
    dx = -0.20 + i * 0.10
    dz = 2.60 + 0.03 * abs(i - 2)
    cone("Tooth low", (dx, -0.845, dz), 0.042, 0.0, 0.12, M["white"],
         verts=8)

rng = random.Random(11)
for sx in (-1, 1):
    cx, cy, cz = sx * 1.02, 0.03, 3.20
    sphere("Hair puff", (cx, cy, cz), 0.58, M["magenta"], segs=48,
           scale=(1.0, 1.0, 1.06))
    for i in range(56):
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1),
                    rng.uniform(-1, 1)))
        if v.length < 0.2:
            continue
        v.normalize()
        p = Vector((cx, cy, cz)) + v * rng.uniform(0.53, 0.60)
        torus("Curl", p, rng.uniform(0.050, 0.105), rng.uniform(0.022, 0.036),
              M["magenta"],
              rot=(rng.uniform(0, math.pi), rng.uniform(0, math.pi),
                   rng.uniform(0, math.pi)),
              mseg=16, nseg=8)
    for i in range(8):
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1),
                    rng.uniform(-1, 1)))
        if v.length < 0.25:
            continue
        v.normalize()
        sphere("Hair ball", Vector((cx, cy, cz)) + v * rng.uniform(0.48, 0.56),
               rng.uniform(0.09, 0.15), M["magenta"], segs=20)

cone("Hat cone", (0, 0.02, 4.545), 0.68, 0.045, 1.05, M["yellow"], verts=64)
torus("Hat brim", (0, 0.02, 4.03), 0.66, 0.10, M["magenta"],
      scale=(1.0, 1.0, 0.75))
cyl("Brim disc", (0, 0.02, 4.00), 0.62, 0.06, M["magenta"], verts=48)
sphere("Pompom", (0, 0.02, 5.14), 0.125, M["lime"], segs=40)

sphere("Torso", (0, 0, 1.58), 1.0, M["green"], segs=56,
       scale=(0.55, 0.43, 0.66))

cyl("Collar base", (0, 0, 2.04), 0.39, 0.10, M["white"], verts=48)
for i in range(12):
    a = i / 12 * math.tau
    sphere("Ruffle", (math.cos(a) * 0.38, math.sin(a) * 0.38, 2.045), 0.14,
           M["white"], segs=24, scale=(1, 1, 0.8))

for sx in (-1, 1):
    sphere("Bow", (sx * 0.155, -0.44, 2.05), 1.0, M["magenta"], segs=32,
           scale=(0.16, 0.07, 0.115), rot=(0, 0, -sx * 0.18))
sphere("Bow knot", (0, -0.47, 2.05), 0.075, M["magenta"], segs=24)

for phi_d in (54, 78, 102, 126, 148):
    for th_d in (-146, -119, -92, -65, -38):
        phi, th = math.radians(phi_d), math.radians(th_d)
        x = 0.55 * math.sin(phi) * math.cos(th)
        y = 0.43 * math.sin(phi) * math.sin(th)
        z = 1.58 + 0.66 * math.cos(phi)
        if y > -0.05:
            continue
        sphere("Polka dot", (x, y, z), 0.062, M["lime"], segs=20,
               scale=(1, 0.5, 1))

for bz in (1.88, 1.66, 1.44):
    by = -0.43 * math.sqrt(max(0.0, 1 - ((bz - 1.58) / 0.66) ** 2))
    sphere("Button", (0, by - 0.01, bz), 0.045, M["lime"], segs=20,
           scale=(1, 0.6, 1))

strap_a = Vector((0.33, -0.30, 1.96))
strap_b = Vector((-0.28, -0.36, 1.16))
slab("Bandolier", strap_a, strap_b, 0.11, 0.035, M["leather"])
strap_dir = (strap_b - strap_a).normalized()
for i in range(6):
    t = 0.14 + i * 0.13
    p = strap_a.lerp(strap_b, t) + Vector((0, -0.048, 0))
    perp = strap_dir.cross(Vector((0, -1, 0))).normalized()
    bar("Shell", p - perp * 0.08, p + perp * 0.08, 0.030, M["brass"])

ARM = {
    "L": {
        "shoulder": Vector((0.52, -0.02, 1.98)),
        "elbow": Vector((0.68, -0.44, 1.78)),
        "wrist": Vector((0.26, -0.86, 1.66)),
        "glove": Vector((0.25, -0.92, 1.66)),
    },
    "R": {
        "shoulder": Vector((-0.52, -0.02, 1.98)),
        "elbow": Vector((-0.62, -0.30, 1.80)),
        "wrist": Vector((-0.20, -0.62, 1.72)),
        "glove": Vector((-0.21, -0.68, 1.71)),
    },
}

for side in ("L", "R"):
    a = ARM[side]
    sphere("Shoulder puff." + side, a["shoulder"] + Vector((0, -0.02, 0.03)),
           0.205, M["green"], segs=40, scale=(1.05, 0.95, 0.95))
    bar("Upper arm." + side, a["shoulder"], a["elbow"], 0.122, M["green"])
    bar("Forearm." + side, a["elbow"], a["wrist"], 0.106, M["green"])
    cuff_dir = (a["wrist"] - a["elbow"]).normalized()
    sphere("Cuff." + side, a["wrist"], 0.142, M["white"], segs=28,
           scale=(1, 1, 0.75))
    sphere("Glove." + side, a["glove"], 0.168, M["white"], segs=32,
           scale=(1.0, 1.08, 1.12))
    sphere("Thumb." + side, a["glove"] + Vector((-0.10 if side == "L" else 0.10,
                                                 0.02, 0.10)), 0.072,
           M["white"], segs=20)

for sx in (-1, 1):
    bar("Leg", (sx * 0.25, 0, 1.02), (sx * 0.27, 0, 0.44), 0.165, M["green"])
    sphere("Trouser cuff", (sx * 0.27, 0, 0.44), 0.180, M["lime"], segs=28,
           scale=(1, 1, 0.55))
    box("Shoe", (sx * 0.29, -0.18, 0.13), (0.40, 0.68, 0.24), M["magenta"],
        bevel=0.09, segs=4)
    sphere("Shoe toe", (sx * 0.29, -0.50, 0.18), 0.17, M["yellow"], segs=32,
           scale=(1.0, 0.95, 0.80))

bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
floor = bpy.context.object
floor.name = "Floor"
floor.data.materials.append(M["ground"])

world = bpy.data.worlds.new("World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.86, 0.86, 0.88, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.5
scene.world = world

def area(name, loc, energy, size, color=(1, 1, 1), target=(0, 0, 2.5)):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = energy
    light.size = size
    light.color = color
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("-Z", "Y")
    return ob

area("Key", (4.0, -6.0, 7.0), 900, 4.5, (1.0, 0.97, 0.93))
area("Fill", (-4.5, -4.5, 3.6), 320, 7.0, (0.90, 0.94, 1.0))
area("Rim", (-1.0, 5.0, 6.0), 650, 4.0, (1.0, 0.98, 0.95))

target = bpy.data.objects.new("CamTarget", None)
scene.collection.objects.link(target)
target.location = (0, 0, 2.55)

cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 50
cam = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam)
cam.location = (3.6, -8.2, 3.5)
con = cam.constraints.new("TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
scene.camera = cam

try:
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
except TypeError:
    pass
scene.view_settings.exposure = -0.15

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
if scene.render.engine == "CYCLES":
    scene.cycles.samples = 64
else:
    try:
        scene.eevee.taa_render_samples = 64
    except AttributeError:
        pass
scene.render.resolution_x = 1000
scene.render.resolution_y = 1250
scene.render.filepath = os.path.join(HERE, "gun_clown_preview.png")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "gun_clown.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "gun_clown.glb"),
                          export_format="GLB")
try:
    bpy.ops.render.render(write_still=True)
except Exception as exc:
    print("RENDER SKIPPED", exc)
print("DONE")
