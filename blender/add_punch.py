
import bpy
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "clown.blend"))
scene = bpy.context.scene
scene.render.fps = 24

rig = bpy.data.objects["ClownRig"]
rig.animation_data_create()
PB = rig.pose.bones
for pb in PB:
    pb.rotation_mode = "XYZ"

lo = 1e9
hi = -1e9
for ob in [o for o in bpy.data.objects if o.type in ("MESH", "CURVE")]:
    for corner in ob.bound_box:
        p = ob.matrix_world @ __import__("mathutils").Vector(corner)
        lo = min(lo, p.z)
        hi = max(hi, p.z)
print("CLOWN Z RANGE", lo, hi, "rig dims", rig.dimensions)

def reset_pose():
    for pb in PB:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    rig.rotation_euler = (0, 0, 0)
    rig.location = (0, 0, 0)

if rig.animation_data:
    for track in list(rig.animation_data.nla_tracks):
        if track.name == "Punch":
            rig.animation_data.nla_tracks.remove(track)
if "Punch" in bpy.data.actions:
    bpy.data.actions.remove(bpy.data.actions["Punch"])
rig.animation_data.action = None

reset_pose()
PB["root"].keyframe_insert("rotation_euler", frame=1)
act = rig.animation_data.action
if act is None:
    raise RuntimeError("Punch action creation failed")
act.name = "Punch"
act.use_fake_user = True
for pb in PB:
    pb.keyframe_insert("rotation_euler", frame=1)
    pb.keyframe_insert("location", frame=1)
rig.keyframe_insert("rotation_euler", frame=1)
rig.keyframe_insert("location", frame=1)

def kf(bone_name, frame, rot=None, loc=None):
    pb = PB[bone_name]
    if rot is not None:
        pb.rotation_euler = tuple(math.radians(a) for a in rot)
        pb.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        pb.location = loc
        pb.keyframe_insert("location", frame=frame)

def okf(frame, rot=None, loc=None):
    if rot is not None:
        rig.rotation_euler = tuple(math.radians(a) for a in rot)
        rig.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        rig.location = loc
        rig.keyframe_insert("location", frame=frame)

kf("hips", 1, rot=(0, 0, 0))
kf("hips", 4, rot=(0, -14, 0))
kf("hips", 8, rot=(0, 16, 0))
kf("hips", 13, rot=(0, 4, 0))
kf("hips", 20, rot=(0, 0, 0))

kf("spine", 1, rot=(0, 0, 0))
kf("spine", 4, rot=(8, -12, 0))
kf("spine", 8, rot=(-6, 14, 0))
kf("spine", 13, rot=(2, 4, 0))
kf("spine", 20, rot=(0, 0, 0))

kf("upper_arm.R", 1, rot=(0, 0, 0))
kf("upper_arm.R", 4, rot=(36, 0, 14))
kf("upper_arm.R", 8, rot=(-28, 0, 82))
kf("upper_arm.R", 11, rot=(-32, 0, 86))
kf("upper_arm.R", 14, rot=(-12, 0, 44))
kf("upper_arm.R", 20, rot=(0, 0, 0))

kf("forearm.R", 1, rot=(0, 0, 0))
kf("forearm.R", 4, rot=(-74, 0, 0))
kf("forearm.R", 8, rot=(0, 0, 0))
kf("forearm.R", 11, rot=(0, 0, 0))
kf("forearm.R", 14, rot=(-26, 0, 0))
kf("forearm.R", 20, rot=(0, 0, 0))

kf("upper_arm.L", 1, rot=(0, 0, 0))
kf("upper_arm.L", 4, rot=(-44, 0, 0))
kf("upper_arm.L", 8, rot=(-58, 0, 0))
kf("upper_arm.L", 14, rot=(-46, 0, 0))
kf("upper_arm.L", 20, rot=(0, 0, 0))

kf("forearm.L", 1, rot=(0, 0, 0))
kf("forearm.L", 4, rot=(-72, 0, 0))
kf("forearm.L", 8, rot=(-86, 0, 0))
kf("forearm.L", 14, rot=(-70, 0, 0))
kf("forearm.L", 20, rot=(0, 0, 0))

kf("head", 1, rot=(0, 0, 0))
kf("head", 4, rot=(4, 10, 0))
kf("head", 8, rot=(-8, -12, 0))
kf("head", 13, rot=(0, -2, 0))
kf("head", 20, rot=(0, 0, 0))

okf(1, loc=(0, 0, 0))
okf(4, loc=(0, 0.08, 0.02))
okf(8, loc=(0, -0.20, -0.03))
okf(11, loc=(0, -0.24, -0.03))
okf(14, loc=(0, -0.10, 0.0))
okf(20, loc=(0, 0, 0))

rig.animation_data.action = None
act.use_fake_user = True
track = rig.animation_data.nla_tracks.new()
track.name = "Punch"
strip = track.strips.new("Punch", 1, act)
try:
    strip.action_slot = act.slots[0]
except Exception as err:
    print("strip slot skipped:", err)
track.mute = True

scene.frame_start = 1
scene.frame_end = 20

cam = bpy.data.objects.get("AnimCam")
if cam is None:
    cam_data = bpy.data.cameras.new("AnimCam")
    cam = bpy.data.objects.new("AnimCam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (4.2, -9.6, 3.0)
    cam.rotation_euler = (math.radians(82), 0, math.radians(24))
scene.camera = cam
try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
try:
    scene.eevee.taa_render_samples = 24
except AttributeError:
    pass
scene.render.resolution_x = 640
scene.render.resolution_y = 640

rig.animation_data.action = act
for frame, label in ((4, "wind"), (9, "strike"), (20, "rest")):
    scene.frame_set(frame)
    scene.render.filepath = os.path.join(HERE, "punch_%s.png" % label)
    bpy.ops.render.render(write_still=True)

rig.animation_data.action = None
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "clown.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "clown.glb"),
                          export_format="GLB", export_animations=True,
                          export_animation_mode="ACTIONS")
print("ACTIONS", [a.name for a in bpy.data.actions])
print("PUNCH DONE")
