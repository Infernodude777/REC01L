"""Render clean, transparent, front-on portrait cuts of both clowns for the intro.

The animation scripts re-saved these .blend files with their own AnimCam rig, so the
camera is rebuilt from the model's real world bounds instead of trusting the file.
"""
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "recoil", "2d Assets", "intro"))
os.makedirs(OUT, exist_ok=True)

JOBS = [
    ("clown.blend", "punch_clown.png"),
    ("gun_clown.blend", "shooter_clown.png"),
]

RES_X, RES_Y = 900, 1200
LENS = 55.0
SENSOR = 36.0
MARGIN = 1.10


def bounds(objects):
    deps = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in objects:
        if ob.type not in ("MESH", "CURVE") or ob.hide_render:
            continue
        ev = ob.evaluated_get(deps)
        mesh = ev.to_mesh()
        mat = ev.matrix_world
        for vertex in mesh.vertices:
            p = mat @ vertex.co
            lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
            hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
        ev.to_mesh_clear()
    return lo, hi


for blend_name, out_name in JOBS:
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, blend_name))
    scene = bpy.context.scene

    for ob in bpy.data.objects:
        if ob.name == "Floor":
            ob.hide_render = True
        if ob.type == "ARMATURE":
            if ob.animation_data:
                ob.animation_data.action = None
            ob.location = (0, 0, 0)
            ob.rotation_euler = (0, 0, 0)
            ob.scale = (1, 1, 1)
            for bone in ob.pose.bones:
                bone.rotation_mode = "QUATERNION"
                bone.rotation_quaternion = (1, 0, 0, 0)
                bone.location = (0, 0, 0)
                bone.scale = (1, 1, 1)

    scene.frame_set(1)
    bpy.context.view_layer.update()

    lo, hi = bounds(bpy.data.objects)
    center = (lo + hi) * 0.5
    height = hi.z - lo.z
    width = hi.x - lo.x

    cam_data = bpy.data.cameras.new("FrontCam")
    cam_data.lens = LENS
    cam_data.sensor_width = SENSOR
    cam_data.sensor_height = SENSOR
    cam_data.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new("FrontCam", cam_data)
    scene.collection.objects.link(cam)

    vfov = 2.0 * math.atan(SENSOR * 0.5 / LENS)
    extent = max(height, width / (RES_X / RES_Y)) * MARGIN
    distance = (extent * 0.5) / math.tan(vfov * 0.5)
    cam.location = (center.x, center.y - distance, center.z)
    cam.rotation_euler = (math.radians(90), 0, math.radians(0))
    scene.camera = cam

    scene.render.film_transparent = True
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = os.path.join(OUT, out_name)

    print("BBOX", blend_name, tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi))
    print("FRAME", blend_name, "height", round(height, 2), "width", round(width, 2),
          "distance", round(distance, 2))

    bpy.ops.render.render(write_still=True)
    print("RENDERED", out_name, os.path.exists(os.path.join(OUT, out_name)))

print("FRONT VIEWS DONE")
