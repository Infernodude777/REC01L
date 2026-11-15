
import bpy
import math
import os
import random
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
TAU = math.tau

R = 17.0
EAVE_Z = 9.0
PEAK_Z = 17.2
N = 32

def make_mat(name, rgb, rough=0.9, metallic=0.0, emission=None,
             strength=0.0, double_sided=True):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if emission is not None:
        if "Emission Color" in b.inputs:
            b.inputs["Emission Color"].default_value = (*emission, 1)
        else:
            b.inputs["Emission"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = strength
    m.use_backface_culling = not double_sided
    return m

M = {
    "red": make_mat("Tent Crimson", (0.240, 0.012, 0.020), 0.92),
    "red_dark": make_mat("Tent Blood", (0.105, 0.006, 0.011), 0.95),
    "cream": make_mat("Tent Bone", (0.620, 0.520, 0.360), 0.90),
    "cream_dirty": make_mat("Tent Bone Stained", (0.420, 0.345, 0.235), 0.95),
    "gold": make_mat("Tent Brass", (0.520, 0.330, 0.085), 0.38, 0.75),
    "wood": make_mat("Tent Wood", (0.090, 0.042, 0.022), 0.80),
    "rope": make_mat("Tent Rope", (0.300, 0.225, 0.120), 0.95),
    "sawdust": make_mat("Tent Sawdust", (0.280, 0.195, 0.105), 0.98),
    "black": make_mat("Tent Void", (0.008, 0.004, 0.006), 1.0),
    "bulb": make_mat("Tent Bulb", (0.25, 0.13, 0.05), 0.4,
                     emission=(1.0, 0.55, 0.16), strength=12.0),
    "pen_red": make_mat("Pennant Red", (0.42, 0.02, 0.03), 0.9),
    "pen_cream": make_mat("Pennant Bone", (0.66, 0.56, 0.38), 0.9),
    "pen_gold": make_mat("Pennant Brass", (0.60, 0.40, 0.10), 0.5, 0.3),
}

def mesh_object(name, verts, faces, mats, face_mats=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    for m in mats:
        me.materials.append(m)
    if face_mats is not None:
        for i, idx in enumerate(face_mats):
            me.polygons[i].material_index = idx
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = smooth
    return ob

def ring_point(a, radius, z):
    return (math.cos(a) * radius, math.sin(a) * radius, z)

rows_z = [0.0, 2.25, 4.5, 6.75, EAVE_Z]
verts = []
for z in rows_z:
    r = R - 0.40 * (z / EAVE_Z)
    for i in range(N):
        verts.append(ring_point(TAU * i / N, r, z))

faces = []
face_mats = []
for row in range(len(rows_z) - 1):
    for i in range(N):
        j = (i + 1) % N
        a = row * N + i
        b = row * N + j
        c = (row + 1) * N + j
        d = (row + 1) * N + i
        faces.append((a, b, c, d))
        face_mats.append(i % 2)
mesh_object("Tent_Walls", verts, faces, [M["red"], M["cream"]], face_mats)

skirt = []
skirt_faces = []
count = 0
for i in range(N):
    j = (i + 1) % N
    a0 = TAU * i / N
    a1 = TAU * j / N
    p0 = ring_point(a0, R + 0.02, 0.0)
    p1 = ring_point(a1, R + 0.02, 0.0)
    p2 = ring_point(a1, R - 0.02, 0.85)
    p3 = ring_point(a0, R - 0.02, 0.85)
    skirt += [p0, p1, p2, p3]
    skirt_faces.append((count, count + 1, count + 2, count + 3))
    count += 4
mesh_object("Tent_Skirt", skirt, skirt_faces, [M["red_dark"]])

val_verts = []
val_faces = []
val_mats = []
for i in range(N):
    a0 = TAU * i / N
    a1 = TAU * (i + 1) / N
    am = (a0 + a1) * 0.5
    r = R - 0.34
    base = len(val_verts)
    p0 = ring_point(a0, r, EAVE_Z)
    p1 = ring_point(a1, r, EAVE_Z)
    b0 = ring_point(a0 + (a1 - a0) * 0.12, r, EAVE_Z - 0.55)
    b1 = ring_point(am, r, EAVE_Z - 1.05)
    b2 = ring_point(a1 - (a1 - a0) * 0.12, r, EAVE_Z - 0.55)
    val_verts += [p0, p1, b2, b1, b0]
    val_faces.append((base, base + 1, base + 2, base + 3))
    val_faces.append((base, base + 3, base + 4))
    val_mats += [i % 2, i % 2]
mesh_object("Tent_Valance", val_verts, val_faces,
            [M["cream"], M["red"]], val_mats)

roof_rings = [(R - 0.40, EAVE_Z), (13.2, 11.3), (9.0, 13.3), (4.6, 15.2), (0.35, PEAK_Z)]
roof_verts = []
for rr, zz in roof_rings:
    for i in range(N):
        roof_verts.append(ring_point(TAU * i / N, rr, zz))
roof_faces = []
roof_mats = []
for row in range(len(roof_rings) - 1):
    for i in range(N):
        j = (i + 1) % N
        a = row * N + i
        b = row * N + j
        c = (row + 1) * N + j
        d = (row + 1) * N + i
        roof_faces.append((a, b, c, d))
        roof_mats.append(i % 2)
mesh_object("Tent_Roof", roof_verts, roof_faces,
            [M["red"], M["cream"]], roof_mats)

def cylinder(name, p1, p2, radius, material, verts_n=12, collect=None):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    if d.length < 1e-5:
        return
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts_n, radius=radius,
                                        depth=d.length, location=(p1 + p2) / 2)
    ob = bpy.context.object
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Z", "Y")
    ob.name = name
    ob.data.materials.append(material)
    if collect is not None:
        collect.append(ob)

trim_parts = []

bpy.ops.mesh.primitive_torus_add(major_radius=16.62, minor_radius=0.085,
                                 major_segments=96, minor_segments=8,
                                 location=(0, 0, EAVE_Z))
ring = bpy.context.object
ring.name = "Eave ring"
ring.data.materials.append(M["gold"])
trim_parts.append(ring)

for i in range(12):
    a = TAU * i / 12 + 0.09
    base = ring_point(a, 16.35, 0.0)
    top = ring_point(a, 16.35, EAVE_Z - 0.02)
    cylinder("Perimeter post", base, top, 0.11, M["wood"], 10, trim_parts)
    cylinder("Post cap", (top[0], top[1], top[2] - 0.02),
             (top[0], top[1], top[2] + 0.22), 0.15, M["gold"], 10, trim_parts)
bpy.ops.object.select_all(action="DESELECT")
for ob in trim_parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = trim_parts[0]
bpy.ops.object.join()
trim_parts[0].name = "Tent_Trim"
for p in trim_parts[0].data.polygons:
    p.use_smooth = True

floor_verts = [(0.0, 0.0, 0.0)]
for i in range(N):
    floor_verts.append(ring_point(TAU * i / N, R + 0.25, 0.0))
floor_faces = []
floor_mats = []
for i in range(N):
    floor_faces.append((0, 1 + i, 1 + (i + 1) % N))
    floor_mats.append(0)

for inner, outer in ((11.6, 12.15), (3.0, 3.35)):
    base = len(floor_verts)
    for i in range(N):
        a0 = TAU * i / N
        a1 = TAU * (i + 1) / N
        floor_verts += [ring_point(a0, inner, 0.005),
                        ring_point(a0, outer, 0.005),
                        ring_point(a1, outer, 0.005),
                        ring_point(a1, inner, 0.005)]
        o = base + i * 4
        floor_faces.append((o, o + 1, o + 2, o + 3))
        floor_mats.append(1)
mesh_object("Tent_Floor", floor_verts, floor_faces,
            [M["sawdust"], M["red_dark"]], floor_mats)

decor_parts = []
random.seed(19)
for i in range(12):
    a = TAU * i / 12 + 0.16
    bx, by = math.cos(a) * 10.6, math.sin(a) * 10.6
    bz = 6.9 + math.sin(i * 1.7) * 0.35
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.16,
                                         location=(bx, by, bz))
    bulb = bpy.context.object
    bulb.name = "Bulb"
    bulb.data.materials.append(M["bulb"])
    decor_parts.append(bulb)
    cylinder("Bulb wire", (bx, by, bz + 0.14),
             (math.cos(a) * 12.2, math.sin(a) * 12.2, 12.6), 0.013,
             M["rope"], 6, decor_parts)

for i in range(N):
    a = TAU * i / N + TAU / (N * 2)
    x, y = math.cos(a) * 16.1, math.sin(a) * 16.1
    z = 8.72
    w = 0.42
    verts_p = [(x - math.sin(a) * w, y + math.cos(a) * w, z + 0.22),
               (x + math.sin(a) * w, y - math.cos(a) * w, z + 0.22),
               (x, y, z - 0.55)]
    faces_p = [(0, 1, 2)]
    mats = [M["pen_red"], M["pen_cream"], M["pen_gold"]]
    pen = mesh_object("Pennant", verts_p, faces_p, [mats[i % 3]])
    decor_parts.append(pen)

curtain_verts = []
curtain_faces = []
base = 0
for i in range(10):
    a0 = math.radians(150 + i * 2.4)
    a1 = math.radians(150 + (i + 1) * 2.4)
    r = R - 0.55
    v0 = ring_point(a0, r, 0.0)
    v1 = ring_point(a1, r, 0.0)
    v2 = ring_point(a1, r, 6.4 - math.sin(i * 0.6) * 0.8)
    v3 = ring_point(a0, r, 6.4 - math.sin(i * 0.6) * 0.8)
    curtain_verts += [v0, v1, v2, v3]
    curtain_faces.append((base, base + 1, base + 2, base + 3))
    base += 4
curtain = mesh_object("Entrance curtain", curtain_verts, curtain_faces, [M["red_dark"]])
decor_parts.append(curtain)

bpy.ops.object.select_all(action="DESELECT")
for ob in decor_parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = decor_parts[0]
bpy.ops.object.join()
decor_parts[0].name = "NH_Decor"
for p in decor_parts[0].data.polygons:
    p.use_smooth = True

world = bpy.data.worlds.new("Tent World")
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs[0].default_value = (0.0035, 0.0022, 0.0030, 1.0)
bg.inputs[1].default_value = 1.0
scene.world = world

def point_light(name, loc, energy, color, radius=0.3):
    light = bpy.data.lights.new(name, "POINT")
    light.energy = energy
    light.color = color
    light.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    return ob

point_light("Peak glow", (0, 0, 14.8), 5200, (1.0, 0.74, 0.46), 1.2)
for i in range(6):
    a = TAU * i / 6 + 0.3
    point_light("Rim lantern", (math.cos(a) * 13.5, math.sin(a) * 13.5, 6.2),
                650, (1.0, 0.52, 0.20), 0.6)

target = bpy.data.objects.new("TentTarget", None)
scene.collection.objects.link(target)
target.location = (0, 0, 4.6)
cam_data = bpy.data.cameras.new("TentCam")
cam_data.lens = 17
cam = bpy.data.objects.new("TentCam", cam_data)
scene.collection.objects.link(cam)
cam.location = (8.6, -10.2, 3.2)
con = cam.constraints.new("TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
scene.camera = cam

try:
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Punchy"
except TypeError:
    try:
        scene.view_settings.view_transform = "Filmic"
    except TypeError:
        pass

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
if scene.render.engine == "CYCLES":
    scene.cycles.samples = 32
else:
    scene.eevee.taa_render_samples = 32
scene.render.resolution_x = 1100
scene.render.resolution_y = 720
scene.render.filepath = os.path.join(HERE, "circus_tent_preview.png")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "circus_tent.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "circus_tent.glb"),
                          export_format="GLB", export_animations=False)
bpy.ops.render.render(write_still=True)
print("TENT DONE", [o.name for o in scene.objects])
