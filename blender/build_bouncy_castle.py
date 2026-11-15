
import bpy
import bmesh
import math
import random
import os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

def make_mat(name, rgb, rough=0.34):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.25
        bsdf.inputs["Coat Roughness"].default_value = 0.12
    return m

MAT = {
    "blue": make_mat("Inflatable Blue", (0.055, 0.16, 0.62)),
    "blue2": make_mat("Inflatable Blue Deep", (0.03, 0.09, 0.42)),
    "yellow": make_mat("Inflatable Yellow", (0.92, 0.58, 0.03)),
    "red": make_mat("Inflatable Red", (0.78, 0.05, 0.07)),
    "green": make_mat("Inflatable Green", (0.03, 0.52, 0.16)),
    "orange": make_mat("Inflatable Orange", (0.90, 0.30, 0.02)),
    "floor": make_mat("Ground", (0.045, 0.045, 0.05), 0.5),
}

def smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True

def box(name, loc, size, mat, bevel=0.06, segs=4, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(mat)
    if bevel > 0:
        b = ob.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = segs
    smooth(ob)
    return ob

def cyl(name, loc, radius, depth, mat, rot=(0, 0, 0), verts=32):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=depth, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(mat)
    smooth(ob)
    return ob

def cone(name, loc, radius, depth, mat):
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=radius, radius2=0.02,
                                    depth=depth, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(mat)
    smooth(ob)
    b = ob.modifiers.new("Bevel", "BEVEL")
    b.width = 0.03
    b.segments = 3
    return ob

def torus(name, loc, major, minor, mat):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=40, minor_segments=12,
                                     location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(mat)
    smooth(ob)
    return ob

def ball(name, loc, r, mat, segs=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=max(6, segs // 2),
                                         radius=r, location=loc)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(mat)
    smooth(ob)
    return ob

def dome(name, loc, r, mat, squash=0.6):
    ob = ball(name, loc, r, mat)
    ob.scale = (1, 1, squash)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return ob

def half_dome(name, loc, r, mat, squash=0.6):
    """Upper half of a squashed ball: its flat rim sits on the surface below."""
    ob = ball(name, loc, r, mat)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:],
                           plane_co=(0, 0, 0), plane_no=(0, 0, 1),
                           clear_inner=True, clear_outer=False)
    bm.to_mesh(ob.data)
    bm.free()
    for v in ob.data.vertices:
        v.co.z *= squash
    return ob

def bar(name, p1, p2, radius, mat, verts=24):
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=d.length,
                                        location=(p1 + p2) / 2)
    ob = bpy.context.object
    ob.name = name
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = d.to_track_quat("Z", "Y")
    ob.data.materials.append(mat)
    smooth(ob)
    return ob

def arch(name, loc, half_w, height, tube, mat, rot=(0, 0, 0)):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(4)
    pts = [(-half_w, 0, 0), (-half_w, 0, height), (0, 0, height + half_w * 0.85),
           (half_w, 0, height), (half_w, 0, 0)]
    for bp, co in zip(sp.bezier_points, pts):
        bp.co = co
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    cu.bevel_depth = tube
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    ob = bpy.data.objects.new(name, cu)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    ob.data.materials.append(mat)
    return ob

def flag(name, loc, mat, size=0.5, rot_z=0.0):
    mesh = bpy.data.meshes.new(name)
    verts = [(0, 0, 0), (0, 0, -size * 0.8), (size, 0, -size * 0.4)]
    mesh.from_pydata(verts, [], [(0, 1, 2)])
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (0, 0, rot_z)
    ob.data.materials.append(mat)
    sol = ob.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.03
    return ob

def bunting(name, x1, x2, y, z, sag=0.55, n=11):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(2)
    pts = [(x1, y, z), ((x1 + x2) / 2, y, z - sag * 2), (x2, y, z)]
    for bp, co in zip(sp.bezier_points, pts):
        bp.co = co
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    cu.bevel_depth = 0.012
    cu.resolution_u = 32
    rope = bpy.data.objects.new(name + " rope", cu)
    scene.collection.objects.link(rope)
    rope.data.materials.append(MAT["yellow"])
    bpy.context.view_layer.update()
    shape = rope.evaluated_get(bpy.context.evaluated_depsgraph_get())
    cooked = shape.to_mesh()
    rope_points = [shape.matrix_world @ v.co for v in cooked.vertices]
    shape.to_mesh_clear()
    pennants = [MAT["red"], MAT["yellow"], MAT["green"], MAT["blue"]]
    for i in range(1, n):
        t = i / n
        px = x1 + (x2 - x1) * t
        near = [p for p in rope_points if abs(p.x - px) < 0.12]
        if not near:
            near = sorted(rope_points, key=lambda p: abs(p.x - px))[:8]
        zs = [p.z for p in near]
        pz = (max(zs) + min(zs)) * 0.5
        flag(name + " pennant", (px, y, pz), pennants[i % 4], 0.36)

DECK = 0.46
FLOOR = DECK + 0.10

box("Base", (0, 4.10, DECK / 2), (16.8, 17.0, DECK), MAT["blue2"], bevel=0.20, segs=5)
box("Deck", (0, 4.10, FLOOR - 0.0485), (16.4, 16.6, 0.097), MAT["blue"], bevel=0.16, segs=5)

def pillar(name, x, y, z0, shaft_h, cone_mat, r=0.22):
    base = z0 - 0.02
    cyl(name + " shaft", (x, y, base + shaft_h / 2), r, shaft_h, MAT["yellow"])
    torus(name + " ring", (x, y, base + shaft_h - 0.062), r + 0.048, 0.062, MAT["blue"])
    cyl(name + " collar", (x, y, base + shaft_h + 0.057), r * 1.07, 0.11, MAT["blue2"])
    cone(name + " spire", (x, y, base + shaft_h + 0.398), r * 1.5, 0.58, MAT[cone_mat])

def bumper_post(name, x, y, h=0.95, r=0.30):
    base = FLOOR - 0.02
    cyl(name + " body", (x, y, base + h / 2), r, h, MAT["yellow"])
    torus(name + " base", (x, y, base + 0.057), r + 0.045, 0.06, MAT["blue"])
    half_dome(name + " cap", (x, y, base + h - 0.012), r * 1.06, MAT["blue"], 0.62)

def hurdle(name, x1, x2, y, h=0.58, z0=FLOOR):
    top = z0 + 0.002 + h
    for x in (x1, x2):
        cyl(name + " post", (x, y, z0 - 0.018 + h / 2), 0.10, h, MAT["blue"], verts=20)
    bar(name + " bar", (x1, y, top), (x2, y, top), 0.10, MAT["red"])

def panel(name, loc, size, mat=None, bevel=0.05):
    return box(name, loc, size, mat or MAT["blue"], bevel=bevel, segs=4)

def window_wall(name, cx, y, w, h):
    """Blue padded wall panel with a framed window opening."""
    panel(name + " panel", (cx, y, FLOOR + h / 2), (w, 0.14, h))
    wz = FLOOR + h * 0.60
    wy = y - 0.09
    ww = min(0.52, w * 0.5)
    wh = h * 0.42
    panel(name + " winL", (cx - ww / 2 - 0.04, wy, wz), (0.09, 0.16, wh + 0.18),
          MAT["blue2"], 0.03)
    panel(name + " winR", (cx + ww / 2 + 0.04, wy, wz), (0.09, 0.16, wh + 0.18),
          MAT["blue2"], 0.03)
    panel(name + " winT", (cx, wy, wz + wh / 2 + 0.06), (ww + 0.18, 0.16, 0.09),
          MAT["blue2"], 0.03)
    panel(name + " winB", (cx, wy, wz - wh / 2 - 0.06), (ww + 0.18, 0.16, 0.09),
          MAT["blue2"], 0.03)

def flume(name, x, y_top, y_bot, z_top, z_bot, width=0.82):
    """One slide flume: red ribbed bed, bulged blue walls, yellow accents.
    Works in either direction along Y."""
    top = Vector((x, y_top, z_top))
    bot = Vector((x, y_bot, z_bot))
    d = bot - top
    L = d.length
    u = d / L
    n = Vector((0, u.z, -u.y))
    if n.z < 0:
        n = -n
    ang = math.atan2(-u.z, -u.y)
    mid = (top + bot) / 2
    down_y = 1.0 if u.y > 0 else -1.0
    box(name + " bed", mid, (width, L, 0.16), MAT["red"],
        bevel=0.05, segs=4, rot=(ang, 0, 0))

    for t in (-0.82, -0.5, -0.18, 0.14, 0.46, 0.78):
        p = mid - u * (t * L / 2) + n * 0.142
        bar(name + " rib", (x - width * 0.44 + 0.012, p.y, p.z),
            (x + width * 0.44 - 0.012, p.y, p.z), 0.06, MAT["red"], verts=16)
    for sx in (-1, 1):
        wx = x + sx * (width / 2 + 0.122)
        p = mid + n * 0.24
        box(name + " wall", (wx, p.y, p.z), (0.24, L, 0.60), MAT["blue"],
            bevel=0.10, segs=6, rot=(ang, 0, 0))
        b1 = bot - u * 0.26 + n * 0.58
        b2 = top + u * 0.26 + n * 0.58
        bar(name + " bulge", (wx, b1.y, b1.z), (wx, b2.y, b2.z), 0.16,
            MAT["blue"], verts=28)
        c1 = bot - u * 0.05 + n * 0.24
        c2 = top + u * 0.05 + n * 0.24
        bar(name + " stripe", (wx + sx * 0.10, c1.y, c1.z),
            (wx + sx * 0.10, c2.y, c2.z), 0.045, MAT["yellow"], verts=14)

    box(name + " canopy", (x, y_top + 0.32 * down_y, z_top + 0.86),
        (width + 0.20, 0.80, 0.17), MAT["green"], bevel=0.075, segs=5,
        rot=(math.radians(-8) * (-down_y), 0, 0))
    box(name + " canopy roll", (x, y_top + 0.72 * down_y, z_top + 0.795),
        (width + 0.16, 0.18, 0.15), MAT["green"], bevel=0.07, segs=5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(name + " canopy post",
                (x + sx * (width / 2 + 0.09), y_top + (0.32 + sy * 0.30) * down_y,
                 z_top + 0.54), 0.055, 0.56, MAT["blue"], verts=16)

ball_mats = [MAT["red"], MAT["yellow"], MAT["green"], MAT["blue"], MAT["orange"]]

def scatter(prefix, cx, cy, w, d, n, floor_top, r0, seed, mats,
            drop=0.95, segs=20):
    """Drop balls so each one rests on the floor or on the balls already there."""
    rr = random.Random(seed)
    placed = []
    for i in range(n):
        for attempt in range(2600):
            shrink = 1.0 if attempt < 900 else (0.94 if attempt < 1600 else 0.62)
            r = r0 * rr.uniform(0.90, 1.08) * shrink
            bx = cx + rr.uniform(-(w / 2 - r - 0.008), w / 2 - r - 0.008)
            by = cy + rr.uniform(-(d / 2 - r - 0.008), d / 2 - r - 0.008)
            bz = floor_top + r + 0.002
            for (ox, oy, oz, orr) in placed:
                dh = math.hypot(bx - ox, by - oy)
                if dh < r + orr:
                    bz = max(bz, oz + math.sqrt((r + orr) ** 2 - dh * dh) + 0.004)
            if bz - r - floor_top > drop:
                continue
            clear = True
            for (ox, oy, oz, orr) in placed:
                gap = (bx - ox) ** 2 + (by - oy) ** 2 + (bz - oz) ** 2
                if gap < (r + orr + 0.004) ** 2:
                    clear = False
                    break
            if not clear:
                continue
            placed.append((bx, by, bz, r))
            ball(prefix + " ball", (bx, by, bz), r, rr.choice(mats), segs=segs)
            break
    print("PIT", prefix, len(placed), "of", n)
    return len(placed)

def ball_pit(name, cx, cy, w, d, n, seed=11, wall_h=0.44, r=0.165):
    t = 0.20
    floor_top = FLOOR + 0.092
    box(name + " floor", (cx, cy, FLOOR + 0.047), (w, d, 0.09), MAT["yellow"],
        bevel=0.04, segs=3)
    for (px, py, sx, sy) in [(cx, cy - (d / 2 + t / 2 + 0.002), w + t * 2, t),
                             (cx, cy + (d / 2 + t / 2 + 0.002), w + t * 2, t),
                             (cx - (w / 2 + t / 2 + 0.002), cy, t, d - 0.004),
                             (cx + (w / 2 + t / 2 + 0.002), cy, t, d - 0.004)]:
        panel(name + " wall", (px, py, FLOOR + 0.002 + wall_h / 2),
              (sx, sy, wall_h), MAT["blue"], 0.07)
    bar(name + " trim", (cx - w / 2 - 0.12, cy - (d / 2 + t / 2 + 0.002),
                         FLOOR + 0.002 + wall_h + 0.052),
        (cx + w / 2 + 0.12, cy - (d / 2 + t / 2 + 0.002),
         FLOOR + 0.002 + wall_h + 0.052), 0.05, MAT["red"])
    scatter(name, cx, cy, w, d, n, floor_top, r, seed, ball_mats, drop=0.62)

HALL_X0, HALL_X1 = -7.9, -3.4
HALL_Y0, HALL_Y1 = -2.6, 2.6

for (px, py) in [(-7.7, -2.4), (-7.7, 2.4), (-3.6, -2.4), (-3.6, 2.4),
                 (-5.65, 2.4), (-5.65, -2.4)]:
    pillar("Hall pillar", px, py, FLOOR, 1.15, "blue", r=0.23)

window_wall("Hall back A", -6.72, 2.42, 1.85, 0.95)
window_wall("Hall back B", -4.62, 2.42, 1.80, 0.95)
panel("Hall side", (-7.78, 0, FLOOR + 0.47), (0.15, 4.55, 0.95))
panel("Hall side cap", (-7.78, 0, FLOOR + 0.98), (0.22, 4.70, 0.22), MAT["green"], 0.10)
bar("Hall top rail", (-7.7, 2.4, FLOOR + 1.00), (-3.6, 2.4, FLOOR + 1.00),
    0.11, MAT["green"])
bar("Hall top rail2", (-7.7, -2.4, FLOOR + 1.00), (-3.6, -2.4, FLOOR + 1.00),
    0.10, MAT["green"])
bar("Hall rail low", (-7.7, -2.4, FLOOR + 0.55), (-3.6, -2.4, FLOOR + 0.55),
    0.09, MAT["red"])

for (y0, y1) in [(-2.4, -0.85), (0.85, 2.4)]:
    panel("Divider", (-3.45, (y0 + y1) / 2, FLOOR + 0.50),
          (0.16, y1 - y0, 1.0))
arch("Divider arch", (-3.45, 0, FLOOR), 0.72, 0.85, 0.10, MAT["red"],
     rot=(0, 0, math.radians(90)))

box("Entry base", (-6.40, -3.35, 0.18), (2.10, 1.30, 0.36), MAT["blue"],
    bevel=0.14, segs=5)
box("Entry pad", (-6.40, -3.35, 0.38), (1.90, 1.15, 0.26), MAT["red"],
    bevel=0.12, segs=5)
for y in (-3.62, -3.34, -3.06):
    bar("Entry bump", (-7.22, y, 0.55), (-5.58, y, 0.55), 0.07, MAT["red"])
arch("Entry arch", (-6.55, -2.62, FLOOR), 0.50, 0.72, 0.09, MAT["red"])

panel("Hall bench", (-7.1, 1.6, FLOOR + 0.18), (1.0, 0.55, 0.36), MAT["red"], 0.10)
panel("Hall bench2", (-5.0, 1.75, FLOOR + 0.18), (1.2, 0.55, 0.36), MAT["orange"], 0.10)

ball_pit("Front pit", 0.10, -3.42, 3.30, 1.15, 48, seed=11)
rng = random.Random(11)

for i, (bx, by) in enumerate([(-4.95, -2.95), (-4.20, -3.55), (-3.55, -2.85),
                              (-2.90, -3.50)]):
    ball("Hop ball", (bx, by, FLOOR + 0.422), 0.42,
         [MAT["red"], MAT["yellow"], MAT["green"], MAT["blue"]][i % 4], segs=28)

for i, (px, py) in enumerate([(-2.75, -1.35), (-1.55, -0.25), (-2.55, 0.85),
                              (-1.05, 1.55), (-2.15, 2.30)]):
    bumper_post("Bumper %d" % i, px, py)

hurdle("Hurdle A", -3.05, -1.25, 2.05)
hurdle("Hurdle B", 0.35, 2.15, 2.55)

for (y0, y1) in [(-1.55, 2.45)]:
    panel("Tunnel wall L", (1.20, (y0 + y1) / 2, FLOOR + 0.27),
          (0.16, y1 - y0, 0.54))
    panel("Tunnel wall R", (2.62, (y0 + y1) / 2, FLOOR + 0.27),
          (0.16, y1 - y0, 0.54))
for i, y in enumerate((-1.15, -0.15, 0.85, 1.85)):
    arch("Tunnel hoop %d" % i, (1.91, y, FLOOR + 0.02), 0.46, 0.52, 0.15,
         MAT["green"])

panel("Tunnel bumper", (1.91, -1.70, FLOOR + 0.24), (1.55, 0.22, 0.48),
      MAT["red"], 0.09)

BR_Y0, BR_Y1 = 2.95, 4.15
for (x0, x1) in [(-3.30, -0.85), (0.85, 3.40)]:
    panel("Back room wall", ((x0 + x1) / 2, 3.05, FLOOR + 0.45),
          (x1 - x0, 0.16, 0.90))
    panel("Back room cap", ((x0 + x1) / 2, 3.05, FLOOR + 0.92),
          (x1 - x0 + 0.06, 0.24, 0.18), MAT["green"], 0.08)
arch("Back room arch", (0, 3.05, FLOOR), 0.74, 0.72, 0.10, MAT["red"])
window_wall("Back room back A", -2.15, 4.15, 2.25, 0.95)
window_wall("Back room back C", 2.45, 4.15, 1.85, 0.95)
arch("North gate", (0.20, 4.15, FLOOR), 1.05, 0.74, 0.10, MAT["red"])
panel("North gate pier L", (-0.95, 4.15, FLOOR + 0.47), (0.30, 0.24, 0.95))
panel("North gate pier R", (1.25, 4.15, FLOOR + 0.47), (0.30, 0.24, 0.95))
panel("Back room side", (3.48, 3.55, FLOOR + 0.47), (0.15, 1.30, 0.95))
panel("Back room side2", (-3.36, 3.55, FLOOR + 0.47), (0.15, 1.30, 0.95))

box("Bounce mattress", (0.15, 3.60, FLOOR + 0.075), (4.30, 0.78, 0.15),
    MAT["red"], bevel=0.07, segs=4)
scatter("Room", 0.15, 3.60, 4.30, 0.78, 8, FLOOR + 0.152, 0.20, 71, ball_mats,
        drop=0.50)
panel("Room pad L", (-2.90, 3.60, FLOOR + 0.16), (0.55, 0.55, 0.32), MAT["green"], 0.08)
panel("Room pad R", (3.05, 3.60, FLOOR + 0.16), (0.55, 0.55, 0.32), MAT["orange"], 0.08)

TX, TY = 6.00, -1.20
TOP = 2.02
box("Tower body", (TX, TY, (FLOOR + TOP) / 2), (3.55, 2.35, TOP - FLOOR),
    MAT["blue"], bevel=0.14, segs=5)
box("Tower deck", (TX, TY, TOP), (3.85, 2.65, 0.20), MAT["blue"],
    bevel=0.14, segs=5)

for sx in (-1, 1):
    for sy in (-1, 1):
        bar("Tower rib", (TX + sx * 1.755, TY + sy * 1.155, FLOOR + 0.10),
            (TX + sx * 1.755, TY + sy * 1.155, TOP), 0.18, MAT["blue"], verts=24)

for (px, py) in [(TX - 1.7, TY - 1.05), (TX + 1.7, TY - 1.05),
                 (TX - 1.7, TY + 1.05), (TX + 1.7, TY + 1.05)]:
    pillar("Tower pillar", px, py, TOP + 0.102, 1.02, "red", r=0.24)

cyl("Spire mast", (TX, TY - 1.05, TOP + 1.15), 0.16, 2.30, MAT["yellow"])
torus("Spire ring", (TX, TY - 1.05, TOP + 1.75), 0.20, 0.05, MAT["blue"])
cone("Spire cone", (TX, TY - 1.05, TOP + 2.45), 0.45, 0.70, MAT["red"])
flag("Spire flag", (TX + 0.02, TY - 1.05, TOP + 2.58), MAT["yellow"], 0.55,
     math.radians(60))

bar("Tower rail back", (TX - 1.7, TY - 1.05, TOP + 1.02),
    (TX + 1.7, TY - 1.05, TOP + 1.02), 0.10, MAT["green"])
bar("Tower rail L", (TX - 1.7, TY - 1.05, TOP + 1.02),
    (TX - 1.7, TY + 1.05, TOP + 1.02), 0.10, MAT["green"])
bar("Tower rail R", (TX + 1.7, TY - 1.05, TOP + 1.02),
    (TX + 1.7, TY + 1.05, TOP + 1.02), 0.10, MAT["green"])

for i in range(6):
    h = 0.28 + i * 0.28
    box("Tower step %d" % i, (3.79, TY - 1.05 + i * 0.44, FLOOR + 0.002 + h / 2),
        (0.56, 0.42, h), MAT["red"] if i % 2 else MAT["blue"],
        bevel=0.07, segs=4)

SL_TOP_Y = TY + 1.15
SL_BOT_Y = 5.00
SL_TOP_Z = TOP + 0.05
SL_BOT_Z = FLOOR + 0.09
for cx in (4.90, 6.00, 7.10):
    flume("Slide", cx, SL_TOP_Y, SL_BOT_Y, SL_TOP_Z, SL_BOT_Z, width=0.82)

    box("Slide stop", (cx, SL_BOT_Y + 0.36, FLOOR + 0.11),
        (0.95, 0.30, 0.22), MAT["red"], bevel=0.10, segs=4)

pillar("Outer tower", 8.02, -3.55, FLOOR, 1.55, "red", r=0.26)
torus("Outer tower ring2", (8.02, -3.55, FLOOR + 0.80), 0.30, 0.07, MAT["green"])

for (px, py) in [(-7.9, -2.4), (-7.9, 2.5), (3.45, -2.4), (3.45, 2.4)]:
    if px < -3.5:
        continue
    pillar("Park pillar", px, py, FLOOR, 1.05, "blue", r=0.22)

flag("Hall flag", (-5.65, 2.40, FLOOR + 1.75), MAT["red"], 0.45, math.radians(15))
flag("Outer flag", (8.02, -3.55, FLOOR + 2.05), MAT["yellow"], 0.48, math.radians(55))

ball_pit("Grand pit", -4.55, 7.72, 5.20, 2.10, 120, seed=23, wall_h=0.56, r=0.19)
for (px, py) in [(-7.45, 6.42), (-7.45, 9.00), (-1.65, 6.42), (-1.65, 9.00)]:
    pillar("Grand pillar", px, py, FLOOR, 1.40, "blue", r=0.25)

window_wall("Grand wall A", -6.35, 9.32, 1.95, 1.05)
window_wall("Grand wall B", -4.35, 9.32, 1.95, 1.05)
window_wall("Grand wall C", -2.25, 9.32, 1.75, 1.05)
panel("Grand side", (-7.78, 7.85, FLOOR + 0.52), (0.15, 3.20, 1.05))
panel("Grand side cap", (-7.78, 7.85, FLOOR + 1.08), (0.24, 3.30, 0.22),
      MAT["green"], 0.10)
bar("Grand rail back", (-7.45, 9.00, FLOOR + 1.20), (-1.65, 9.00, FLOOR + 1.20),
    0.10, MAT["green"])
arch("Grand entry arch", (-4.55, 6.28, FLOOR), 0.97, 0.80, 0.10, MAT["red"])
panel("Grand entry pier L", (-5.52, 6.28, FLOOR + 0.46), (0.32, 0.22, 0.92),
      MAT["blue"], 0.07)
panel("Grand entry pier R", (-3.58, 6.28, FLOOR + 0.46), (0.32, 0.22, 0.92),
      MAT["blue"], 0.07)
box("Grand entry pad", (-4.55, 5.86, FLOOR + 0.05), (2.25, 0.62, 0.10),
    MAT["red"], bevel=0.09, segs=4)

for i, (x0, x1, yy) in enumerate([(0.35, 2.05, 6.35), (1.35, 3.25, 7.45),
                                  (0.35, 2.20, 8.55)]):
    panel("Maze wall %d" % i, ((x0 + x1) / 2, yy, FLOOR + 0.36),
          (x1 - x0, 0.20, 0.72), MAT["red"] if i % 2 else MAT["blue"], 0.08)
    bar("Maze cap %d" % i, (x0, yy, FLOOR + 0.75), (x1, yy, FLOOR + 0.75),
        0.06, MAT["green"])
hurdle("North hurdle A", 0.45, 2.05, 5.55, h=0.50)
hurdle("North hurdle B", 1.20, 3.00, 9.35, h=0.55)
for i, (px, py) in enumerate([(3.20, 8.35), (0.60, 9.55), (2.55, 10.80)]):
    bumper_post("North bumper %d" % i, px, py, h=0.85, r=0.28)
for i, (bx, by) in enumerate([(3.15, 11.30), (1.75, 11.90), (3.05, 6.05)]):
    ball("North hop", (bx, by, FLOOR + 0.402), 0.40,
         [MAT["yellow"], MAT["green"], MAT["red"]][i % 3], segs=26)

box("Courtyard mattress", (-4.55, 11.45, FLOOR + 0.08), (5.40, 0.90, 0.16),
    MAT["red"], bevel=0.07, segs=4)
for i, bx in enumerate((-6.10, -4.55, -3.00)):
    ball("Courtyard ball", (bx, 11.45, FLOOR + 0.50), 0.34,
         [MAT["yellow"], MAT["green"], MAT["orange"]][i], segs=24)
for (px, py) in [(-7.55, 10.35), (-1.75, 10.35)]:
    pillar("Rear pillar", px, py, FLOOR, 1.10, "red", r=0.23)

panel("Rear side", (-7.78, 10.75, FLOOR + 0.52), (0.15, 2.95, 1.05))
window_wall("North wall A", -5.80, 12.30, 2.15, 1.05)
window_wall("North wall B", -3.45, 12.30, 2.15, 1.05)
window_wall("North wall C", -1.15, 12.30, 2.10, 1.05)
window_wall("North wall D", 1.25, 12.30, 2.05, 1.05)
window_wall("North wall E", 3.55, 12.30, 1.90, 1.05)
for py in (12.20,):
    for px in (-7.55, -4.60, -1.65, 1.30, 4.25):
        pillar("North pillar", px, py, FLOOR, 1.30, "red", r=0.24)

TX2, TY2 = 5.95, 10.80
TOP2 = FLOOR + 1.30
box("Tower2 body", (TX2, TY2, (FLOOR + TOP2) / 2), (2.40, 2.00, TOP2 - FLOOR),
    MAT["blue"], bevel=0.13, segs=5)
box("Tower2 deck", (TX2, TY2, TOP2), (2.75, 2.30, 0.18), MAT["blue"],
    bevel=0.13, segs=5)
for sx in (-1, 1):
    for sy in (-1, 1):
        bar("Tower2 rib", (TX2 + sx * 1.18, TY2 + sy * 0.98, FLOOR + 0.10),
            (TX2 + sx * 1.18, TY2 + sy * 0.98, TOP2), 0.15, MAT["blue"], verts=22)
for (px, py) in [(TX2 - 1.15, TY2 - 0.90), (TX2 + 1.15, TY2 - 0.90),
                 (TX2 - 1.15, TY2 + 0.90), (TX2 + 1.15, TY2 + 0.90)]:
    pillar("Tower2 pillar", px, py, TOP2 + 0.092, 0.92, "red", r=0.22)
cyl("Tower2 mast", (TX2, TY2 + 0.90, TOP2 + 0.90), 0.14, 1.75, MAT["yellow"])
cone("Tower2 cone", (TX2, TY2 + 0.90, TOP2 + 1.95), 0.38, 0.62, MAT["red"])
flag("Tower2 flag", (TX2 + 0.02, TY2 + 0.90, TOP2 + 2.06), MAT["green"], 0.46,
     math.radians(25))
bar("Tower2 rail back", (TX2 - 1.15, TY2 + 0.90, TOP2 + 0.82),
    (TX2 + 1.15, TY2 + 0.90, TOP2 + 0.82), 0.09, MAT["green"])
for sx in (-1, 1):
    bar("Tower2 rail side", (TX2 + sx * 1.15, TY2 - 0.90, TOP2 + 0.82),
        (TX2 + sx * 1.15, TY2 + 0.90, TOP2 + 0.82), 0.09, MAT["green"])

for cx in (5.30, 6.60):
    flume("Slide N", cx, TY2 - 1.05, 6.05, TOP2 + 0.05, FLOOR + 0.09, width=0.80)
    box("Slide N stop", (cx, 5.70, FLOOR + 0.10), (0.92, 0.30, 0.20), MAT["red"],
        bevel=0.10, segs=4)
box("North landing", (5.95, 6.35, FLOOR + 0.062), (3.30, 1.55, 0.12), MAT["blue"],
    bevel=0.14, segs=5)

for i in range(5):
    h = 0.30 + i * 0.34
    box("Tower2 step %d" % i, (4.30, 9.55 + i * 0.40, FLOOR + 0.002 + h / 2),
        (0.54, 0.37, h), MAT["red"] if i % 2 else MAT["blue"], bevel=0.07, segs=4)

R_PILLARS = [5.40, 8.20, 10.90]
for py in R_PILLARS:
    pillar("Edge pillar", 8.02, py, FLOOR, 1.15, "blue", r=0.23)
for a, b in zip(R_PILLARS, R_PILLARS[1:]):
    bar("Edge rail", (8.02, a, FLOOR + 0.95), (8.02, b, FLOOR + 0.95), 0.10,
        MAT["green"])

bunting("Grand bunting", -7.45, -1.65, 6.42, FLOOR + 1.34, sag=0.45, n=13)
bunting("Rear bunting", -7.55, -1.75, 10.35, FLOOR + 1.05, sag=0.32, n=9)
flag("Grand flag", (-1.65, 9.00, FLOOR + 2.02), MAT["yellow"], 0.44,
     math.radians(-20))

bpy.ops.mesh.primitive_plane_add(size=90, location=(0, 0, 0))
ground = bpy.context.object
ground.name = "Ground"
ground.data.materials.append(MAT["floor"])

world = bpy.data.worlds.new("World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.026, 0.028, 0.033, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
scene.world = world

def area(name, energy, size, loc, rot, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA")
    l.energy = energy
    l.size = size
    l.color = color
    ob = bpy.data.objects.new(name, l)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    return ob

area("Key", 7000, 7.0, (9, -14, 13), (math.radians(48), 0, math.radians(32)),
     (1.0, 0.96, 0.90))
area("Fill", 2200, 10.0, (-13, -8, 9), (math.radians(65), 0, math.radians(-60)),
     (0.80, 0.86, 1.0))
area("Rim", 4000, 6.0, (-4, 17, 12), (math.radians(118), 0, math.radians(190)),
     (0.9, 0.95, 1.0))
area("Front Fill", 1200, 8.0, (2, -16, 4), (math.radians(80), 0, 0))
area("North Key", 5200, 8.0, (4, 13, 13), (math.radians(-28), 0, math.radians(-10)),
     (1.0, 0.97, 0.92))

target = bpy.data.objects.new("CamTarget", None)
scene.collection.objects.link(target)

bunting("Front bunting", -3.50, 3.45, -2.40, FLOOR + 1.00, sag=0.22, n=12)
bunting("Hall bunting", -7.70, -3.60, -2.40, FLOOR + 1.10, sag=0.35, n=10)

bar("Trim front", (-8.02, -4.14, FLOOR + 0.092), (8.02, -4.14, FLOOR + 0.092),
    0.09, MAT["red"])
bar("Trim right", (8.12, -4.04, FLOOR + 0.092), (8.12, 12.24, FLOOR + 0.092),
    0.09, MAT["red"])
bar("Trim left", (-8.12, -4.04, FLOOR + 0.092), (-8.12, 12.24, FLOOR + 0.092),
    0.09, MAT["red"])
bar("Trim back", (-8.02, 12.34, FLOOR + 0.092), (8.02, 12.34, FLOOR + 0.092),
    0.09, MAT["red"])

target.location = (0.2, 3.6, 1.00)

cam_data = bpy.data.cameras.new("Camera")
cam_data.lens = 45
cam = bpy.data.objects.new("Camera", cam_data)
scene.collection.objects.link(cam)
cam.location = (13.5, -19.0, 18.5)
con = cam.constraints.new("TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
scene.camera = cam

for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
    try:
        scene.render.engine = eng
        break
    except TypeError:
        continue
if scene.render.engine == "CYCLES":
    scene.cycles.samples = 40
else:
    scene.eevee.taa_render_samples = 40
scene.render.resolution_x = 1280
scene.render.resolution_y = 840
scene.render.filepath = os.path.join(HERE, "preview.png")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "bouncy_castle.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "bouncy_castle.glb"),
                          export_format="GLB")
bpy.ops.render.render(write_still=True)
print("DONE")
