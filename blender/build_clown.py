
import bpy
import bmesh
import math
import os
import random
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def make_mat(name, rgb, rough=0.4):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 0.12
        b.inputs["Coat Roughness"].default_value = 0.25
    return m

M = {
    "skin": make_mat("Skin White", (0.95, 0.92, 0.89), 0.38),
    "white": make_mat("White", (0.98, 0.98, 0.97), 0.32),
    "red": make_mat("Clown Red", (0.80, 0.02, 0.03), 0.30),
    "pink": make_mat("Cheek Pink", (0.96, 0.34, 0.45), 0.42),
    "blue": make_mat("Clown Blue", (0.03, 0.15, 0.66), 0.36),
    "green": make_mat("Clown Green", (0.04, 0.52, 0.13), 0.36),
    "yellow": make_mat("Clown Yellow", (0.97, 0.66, 0.02), 0.36),
    "magenta": make_mat("Hat Magenta", (0.86, 0.03, 0.40), 0.36),
    "orange": make_mat("Hair Orange", (0.95, 0.28, 0.02), 0.52),
    "black": make_mat("Black", (0.012, 0.012, 0.014), 0.24),
    "dark": make_mat("Mouth Dark", (0.16, 0.008, 0.018), 0.55),
    "ground": make_mat("Studio Floor", (0.88, 0.87, 0.86), 0.9),
}

HEAD_C = Vector((0, 0, 3.12))
HEAD_R = Vector((0.969, 0.931, 1.045))

def face_y(x, z):
    """Y of the head surface at (x, z), on the camera side."""
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

sphere("Head", HEAD_C, 0.95, M["skin"], segs=64,
       scale=(1.02, 0.98, 1.10))
cyl("Neck", (0, 0, 2.13), 0.22, 0.50, M["skin"])

for sx in (-1, 1):
    sphere("Cheek", (sx * 0.56, -0.68, 2.96), 0.225, M["pink"], segs=40,
           scale=(1.0, 0.52, 0.82))

for sx in (-1, 1):
    sphere("Eye", (sx * 0.33, -0.79, 3.38), 0.21, M["white"], segs=48,
           scale=(1.0, 0.72, 1.18))
    sphere("Pupil", (sx * 0.33, -0.905, 3.37), 0.092, M["black"], segs=32,
           scale=(1.0, 0.52, 1.15))
    sphere("Eye glint", (sx * 0.30, -0.952, 3.43), 0.033, M["white"], segs=20)

for sx in (-1, 1):
    for i, t in enumerate((-0.8, -0.4, 0.0, 0.4, 0.8)):
        bx = sx * 0.35 + t * 0.17
        bz = 3.575 + (1 - t * t) * 0.065
        sphere("Brow", (bx, face_y(bx, bz) + 0.012, bz), 0.052, M["blue"],
               segs=24, scale=(1.0, 0.85, 0.95))

sphere("Nose", (0, -0.98, 3.10), 0.195, M["red"], segs=48,
       scale=(1.05, 1.0, 0.95))
sphere("Nose glint", (0.07, -1.165, 3.18), 0.035, M["white"], segs=20)

lip_pts = [
    (-0.45, -0.800, 2.79), (-0.27, -0.855, 2.865), (0.0, -0.870, 2.88),
    (0.27, -0.855, 2.865), (0.45, -0.800, 2.79), (0.32, -0.800, 2.56),
    (0.0, -0.845, 2.45), (-0.32, -0.800, 2.56),
]
curve_tube("Lips", lip_pts, 0.072, M["red"], cyclic=True)
sphere("Mouth", (0, -0.815, 2.665), 1.0, M["dark"], segs=40,
       scale=(0.37, 0.10, 0.185))
for i, dx in enumerate((-0.20, -0.10, 0.0, 0.10, 0.20)):
    box("Tooth", (dx, -0.890 + 0.01 * abs(i - 2),
                  2.800 - 0.02 * abs(i - 2)), (0.086, 0.030, 0.100),
        M["white"], bevel=0.020, segs=3)
sphere("Tongue", (0, -0.875, 2.52), 1.0, M["red"], segs=32,
       scale=(0.21, 0.050, 0.080))

rng = random.Random(7)
for sx in (-1, 1):
    cx, cy, cz = sx * 1.03, 0.03, 3.10
    sphere("Hair puff", (cx, cy, cz), 0.60, M["orange"], segs=48,
           scale=(1.0, 1.0, 1.05))
    for i in range(64):
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1),
                    rng.uniform(-1, 1)))
        if v.length < 0.2:
            continue
        v.normalize()
        p = Vector((cx, cy, cz)) + v * rng.uniform(0.55, 0.63)
        torus("Curl", p, rng.uniform(0.055, 0.115), rng.uniform(0.024, 0.040),
              M["orange"],
              rot=(rng.uniform(0, math.pi), rng.uniform(0, math.pi),
                   rng.uniform(0, math.pi)),
              mseg=16, nseg=8)
    for i in range(10):
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1),
                    rng.uniform(-1, 1)))
        if v.length < 0.25:
            continue
        v.normalize()
        sphere("Hair ball", Vector((cx, cy, cz)) + v * rng.uniform(0.50, 0.58),
               rng.uniform(0.10, 0.16), M["orange"], segs=20)

bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0,
                                     location=(0, 0, 0))
hat = bpy.context.object
hat.name = "Hat dome"
bm = bmesh.new()
bm.from_mesh(hat.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.001],
                 context="VERTS")
bm.to_mesh(hat.data)
bm.free()
hat.scale = (0.68, 0.68, 0.78)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
hat.location = (0, 0.02, 4.02)
for key in ("blue", "green", "yellow", "red"):
    hat.data.materials.append(M[key])
for p in hat.data.polygons:
    a = math.atan2(p.center.y, p.center.x)
    idx = int(((a + math.pi) / (2 * math.pi)) * 8) % 4
    p.material_index = idx
smooth(hat)

torus("Hat brim", (0, 0.02, 4.02), 0.72, 0.13, M["magenta"],
      scale=(1.0, 1.0, 0.70))
cyl("Brim disc", (0, 0.02, 4.00), 0.72, 0.07, M["magenta"], verts=48)

cyl("Pompom stalk", (0.42, 0.02, 4.68), 0.032, 0.30, M["yellow"],
    rot=(0, math.radians(52), 0))
sphere("Pompom", (0.55, 0.02, 4.80), 0.14, M["yellow"], segs=40)

sphere("Torso", (0, 0, 1.56), 1.0, M["blue"], segs=56,
       scale=(0.62, 0.47, 0.70))

cyl("Collar base", (0, 0, 2.03), 0.43, 0.10, M["white"], verts=48)
for i in range(14):
    a = i / 14 * math.tau
    sphere("Ruffle", (math.cos(a) * 0.42, math.sin(a) * 0.42, 2.025), 0.15,
           M["white"], segs=24, scale=(1, 1, 0.8))

for sx in (-1, 1):
    sphere("Bow", (sx * 0.165, -0.47, 2.05), 1.0, M["red"], segs=32,
           scale=(0.17, 0.075, 0.12), rot=(0, 0, -sx * 0.18))
sphere("Bow knot", (0, -0.50, 2.05), 0.08, M["red"], segs=24)

for phi_d in (50, 74, 98, 122, 144):
    for th_d in (-144, -117, -90, -63, -36):
        phi, th = math.radians(phi_d), math.radians(th_d)
        x = 0.62 * math.sin(phi) * math.cos(th)
        y = 0.47 * math.sin(phi) * math.sin(th)
        z = 1.56 + 0.70 * math.cos(phi)
        if y > -0.05:
            continue
        sphere("Polka dot", (x, y, z), 0.066, M["yellow"], segs=20,
               scale=(1, 0.5, 1))

for bz in (1.86, 1.64, 1.42):
    by = -0.47 * math.sqrt(max(0.0, 1 - ((bz - 1.56) / 0.70) ** 2))
    sphere("Button", (0, by - 0.01, bz), 0.048, M["yellow"], segs=20,
           scale=(1, 0.6, 1))

for sx in (-1, 1):
    sphere("Shoulder puff", (sx * 0.54, 0, 2.02), 0.23, M["blue"], segs=40,
           scale=(1.05, 0.95, 0.95))
    bar("Upper arm", (sx * 0.57, 0, 1.98), (sx * 0.88, -0.04, 1.62), 0.13,
        M["blue"])
    bar("Forearm", (sx * 0.88, -0.04, 1.62), (sx * 1.00, -0.10, 1.24), 0.115,
        M["blue"])
    sphere("Cuff", (sx * 1.00, -0.10, 1.22), 0.155, M["white"], segs=28,
           scale=(1, 1, 0.72))
    sphere("Glove", (sx * 1.03, -0.14, 1.09), 0.185, M["white"], segs=32,
           scale=(1.0, 1.05, 1.15))
    sphere("Thumb", (sx * 0.93, -0.26, 1.12), 0.08, M["white"], segs=20)

for sx in (-1, 1):
    bar("Leg", (sx * 0.26, 0, 1.04), (sx * 0.29, 0, 0.42), 0.180, M["blue"])
    sphere("Trouser cuff", (sx * 0.29, 0, 0.42), 0.190, M["red"], segs=28,
           scale=(1, 1, 0.55))
    box("Shoe", (sx * 0.30, -0.20, 0.14), (0.40, 0.72, 0.26), M["red"],
        bevel=0.10, segs=4)
    sphere("Shoe toe", (sx * 0.30, -0.54, 0.19), 0.18, M["yellow"], segs=32,
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
target.location = (0, 0, 2.45)

cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 50
cam = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam)
cam.location = (3.4, -8.0, 3.4)
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
    scene.eevee.taa_render_samples = 64
scene.render.resolution_x = 1000
scene.render.resolution_y = 1250
scene.render.filepath = os.path.join(HERE, "clown_preview.png")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "clown.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "clown.glb"),
                          export_format="GLB")
bpy.ops.render.render(write_still=True)
print("DONE")
