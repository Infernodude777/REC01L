
import bpy
import math
import os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "clown.blend"))
if "ClownRig" in bpy.data.objects:
    raise SystemExit("clown.blend is already rigged - rebuild the base with build_clown.py first")
scene = bpy.context.scene
scene.render.fps = 24

bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
arm = bpy.context.object
arm.name = "ClownRig"
arm.data.name = "ClownRig"
eb = arm.data.edit_bones
for b in list(eb):
    eb.remove(b)

def bone(name, head, tail, parent=None):
    b = eb.new(name)
    b.head = head
    b.tail = tail
    if parent:
        b.parent = eb[parent]
    b.use_connect = False
    return b

bone("root", (0, 0, 0.0), (0, 0, 0.30))
bone("hips", (0, 0, 1.00), (0, 0, 1.35), "root")
bone("spine", (0, 0, 1.35), (0, 0, 2.05), "hips")
bone("head", (0, 0, 2.05), (0, 0, 3.60), "spine")
for s, sx in (("L", 1.0), ("R", -1.0)):
    bone("upper_arm." + s, (sx * 0.56, 0, 2.00), (sx * 0.88, -0.04, 1.62), "spine")
    bone("forearm." + s, (sx * 0.88, -0.04, 1.62), (sx * 1.00, -0.10, 1.22),
         "upper_arm." + s)
    bone("hand." + s, (sx * 1.00, -0.10, 1.22), (sx * 1.05, -0.14, 1.02),
         "forearm." + s)
    bone("thigh." + s, (sx * 0.26, 0, 1.05), (sx * 0.29, 0, 0.42), "hips")
    bone("foot." + s, (sx * 0.29, 0, 0.42), (sx * 0.30, -0.40, 0.14),
         "thigh." + s)
bpy.ops.object.mode_set(mode="OBJECT")
arm.show_in_front = True

HEAD_PARTS = ("Head", "Cheek", "Eye", "Pupil", "Brow", "Nose", "Lips", "Mouth",
              "Tooth", "Tongue", "Hair puff", "Curl", "Hair ball", "Hat dome",
              "Hat brim", "Brim disc", "Pompom")
SPINE_PARTS = ("Torso", "Collar base", "Ruffle", "Bow", "Bow knot", "Polka dot",
               "Button", "Shoulder puff", "Neck")
groups = {name: [] for name in (
    "head", "spine", "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R",
    "hand.L", "hand.R", "thigh.L", "thigh.R", "foot.L", "foot.R")}

for ob in [o for o in bpy.data.objects if o.type in ("MESH", "CURVE")]:
    if ob.name in ("Floor", "CamTarget", "AnimTarget"):
        continue
    n = ob.name
    sx = ob.matrix_world.translation.x
    side = "L" if sx > 0 else "R"
    if n.startswith(HEAD_PARTS):
        groups["head"].append(ob)
    elif n.startswith("Upper arm"):
        groups["upper_arm." + side].append(ob)
    elif n.startswith(("Forearm", "Cuff")):
        groups["forearm." + side].append(ob)
    elif n.startswith(("Glove", "Thumb")):
        groups["hand." + side].append(ob)
    elif n.startswith(("Leg", "Trouser cuff")):
        groups["thigh." + side].append(ob)
    elif n.startswith("Shoe"):
        groups["foot." + side].append(ob)
    else:
        groups["spine"].append(ob)

def parent_group(bone_name, objs):
    if not objs:
        return
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    arm.data.bones.active = arm.data.bones[bone_name]
    bpy.ops.object.parent_set(type="BONE", keep_transform=True)

for name, objs in groups.items():
    parent_group(name, objs)

arm.animation_data_create()
PB = arm.pose.bones
for pb in PB:
    pb.rotation_mode = "XYZ"

def reset_pose():
    for pb in PB:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    arm.rotation_euler = (0, 0, 0)
    arm.location = (0, 0, 0)

def new_action(name):
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    reset_pose()
    for pb in PB:
        pb.keyframe_insert("rotation_euler", frame=1)
        pb.keyframe_insert("location", frame=1)
    arm.keyframe_insert("rotation_euler", frame=1)
    arm.keyframe_insert("location", frame=1)
    return act

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
        arm.rotation_euler = tuple(math.radians(a) for a in rot)
        arm.keyframe_insert("rotation_euler", frame=frame)
    if loc is not None:
        arm.location = loc
        arm.keyframe_insert("location", frame=frame)

def stash(act):
    arm.animation_data.action = None
    act.use_fake_user = True
    track = arm.animation_data.nla_tracks.new()
    track.name = act.name
    track.strips.new(act.name, 1, act)
    track.mute = True

act = new_action("Walk")
for f, a in ((1, -24), (7, 0), (13, 24), (19, 0), (25, -24)):
    kf("thigh.L", f, rot=(a, 0, 0))
for f, a in ((1, 24), (7, 0), (13, -24), (19, 0), (25, 24)):
    kf("thigh.R", f, rot=(a, 0, 0))
for f, a in ((1, 20), (7, 0), (13, -20), (19, 0), (25, 20)):
    kf("upper_arm.L", f, rot=(a, 0, 0))
for f, a in ((1, -20), (7, 0), (13, 20), (19, 0), (25, -20)):
    kf("upper_arm.R", f, rot=(a, 0, 0))
kf("forearm.L", 1, rot=(-10, 0, 0))
kf("forearm.R", 1, rot=(-10, 0, 0))
kf("spine", 1, rot=(0, 4, 0))
kf("spine", 13, rot=(0, -4, 0))
kf("spine", 25, rot=(0, 4, 0))
kf("head", 1, rot=(0, -3, 0))
kf("head", 25, rot=(0, -3, 0))
stash(act)

act = new_action("Run")
for f, a in ((1, -42), (5, 0), (9, 42), (13, 0), (17, -42)):
    kf("thigh.L", f, rot=(a, 0, 0))
for f, a in ((1, 42), (5, 0), (9, -42), (13, 0), (17, 42)):
    kf("thigh.R", f, rot=(a, 0, 0))
for f, a in ((1, 38), (5, 0), (9, -38), (13, 0), (17, 38)):
    kf("upper_arm.L", f, rot=(a, 0, 0))
for f, a in ((1, -38), (5, 0), (9, 38), (13, 0), (17, -38)):
    kf("upper_arm.R", f, rot=(a, 0, 0))
for s in ("L", "R"):
    kf("forearm." + s, 1, rot=(-45, 0, 0))
kf("spine", 1, rot=(12, 0, 0))
kf("spine", 17, rot=(12, 0, 0))
kf("head", 1, rot=(-10, 0, 0))
kf("head", 17, rot=(-10, 0, 0))
stash(act)

act = new_action("Aim")
okf(8, rot=(0, 0, -40))
okf(16, rot=(0, 0, -45))
okf(19, rot=(0, 0, -38))
okf(24, rot=(0, 0, -28))
okf(30, rot=(0, 0, 0))
kf("spine", 8, rot=(6, 0, 0))
kf("spine", 16, rot=(4, 0, 0))
kf("spine", 19, rot=(-6, 0, 0))
kf("spine", 24, rot=(2, 0, 0))
kf("spine", 30, rot=(0, 0, 0))

kf("upper_arm.R", 8, rot=(-92, 0, 0))
kf("upper_arm.R", 16, rot=(-95, 0, 0))
kf("upper_arm.R", 19, rot=(-104, 0, 0))
kf("upper_arm.R", 24, rot=(-90, 0, 0))
kf("upper_arm.R", 30, rot=(0, 0, 0))
kf("forearm.R", 8, rot=(-6, 0, 0))
kf("forearm.R", 16, rot=(-5, 0, 0))
kf("forearm.R", 19, rot=(-18, 0, 0))
kf("forearm.R", 24, rot=(-4, 0, 0))
kf("forearm.R", 30, rot=(0, 0, 0))
kf("upper_arm.L", 8, rot=(-55, 0, 0))
kf("upper_arm.L", 16, rot=(-58, 0, 0))
kf("upper_arm.L", 19, rot=(-66, 0, 0))
kf("upper_arm.L", 24, rot=(-52, 0, 0))
kf("upper_arm.L", 30, rot=(0, 0, 0))
kf("forearm.L", 8, rot=(-55, 0, 0))
kf("forearm.L", 16, rot=(-58, 0, 0))
kf("forearm.L", 19, rot=(-70, 0, 0))
kf("forearm.L", 24, rot=(-50, 0, 0))
kf("forearm.L", 30, rot=(0, 0, 0))
kf("head", 8, rot=(4, 0, 0))
kf("head", 19, rot=(-6, 0, 0))
kf("head", 30, rot=(0, 0, 0))
stash(act)

act = new_action("Die")
okf(4, rot=(-6, 0, 0))
okf(9, rot=(-20, 0, 0))
okf(20, rot=(-50, 0, 0), loc=(0, 0, 0.10))
okf(24, rot=(-57, 0, 0), loc=(0, 0, 0.12))
okf(30, rot=(-57, 0, 0), loc=(0, 0, 0.12))
for s in ("L", "R"):
    kf("upper_arm." + s, 6, rot=(-120, 0, 0))
    kf("upper_arm." + s, 20, rot=(-100, 0, 0))
    kf("upper_arm." + s, 30, rot=(-95, 0, 0))
    kf("forearm." + s, 6, rot=(-25, 0, 0))
    kf("forearm." + s, 30, rot=(-15, 0, 0))
    kf("thigh." + s, 20, rot=(18, 0, 0))
    kf("thigh." + s, 30, rot=(22, 0, 0))
kf("spine", 4, rot=(-8, 0, 0))
kf("spine", 12, rot=(-16, 0, 0))
kf("spine", 20, rot=(6, 0, 0))
kf("spine", 30, rot=(4, 0, 0))
kf("head", 6, rot=(-14, 0, 0))
kf("head", 20, rot=(14, 0, 0))
kf("head", 30, rot=(10, 0, 0))
stash(act)

act = new_action("Idle")
kf("spine", 1, rot=(0, 0, 0))
kf("spine", 13, rot=(2, 0, 0))
kf("spine", 25, rot=(0, 0, 0))
kf("spine", 37, rot=(2, 0, 0))
kf("spine", 49, rot=(0, 0, 0))
kf("head", 1, rot=(0, -4, 0))
kf("head", 25, rot=(0, 4, 0))
kf("head", 49, rot=(0, -4, 0))
for s in ("L", "R"):
    kf("upper_arm." + s, 1, rot=(0, 0, 0))
    kf("upper_arm." + s, 25, rot=(3, 0, 0))
    kf("upper_arm." + s, 49, rot=(0, 0, 0))
stash(act)

target = bpy.data.objects.new("AnimTarget", None)
scene.collection.objects.link(target)
target.location = (0, 0.8, 2.0)

cam_data = bpy.data.cameras.new("AnimCam")
cam_data.lens = 40
cam = bpy.data.objects.new("AnimCam", cam_data)
scene.collection.objects.link(cam)
cam.location = (4.6, -10.8, 4.6)
con = cam.constraints.new("TRACK_TO")
con.target = target
con.track_axis = "TRACK_NEGATIVE_Z"
con.up_axis = "UP_Y"
scene.camera = cam

scene.render.resolution_x = 600
scene.render.resolution_y = 600
try:
    scene.eevee.taa_render_samples = 20
except AttributeError:
    pass

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "clown.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "clown.glb"),
                          export_format="GLB", export_animations=True)

checks = (("Walk", 1, "walk1"), ("Walk", 13, "walk13"), ("Run", 1, "run1"),
          ("Aim", 16, "aim"), ("Die", 24, "die"), ("Idle", 25, "idle"))
for act_name, frame, label in checks:
    reset_pose()
    act = bpy.data.actions[act_name]
    arm.animation_data.action = act
    scene.frame_set(frame)
    scene.render.filepath = os.path.join(HERE, "pose_%s.png" % label)
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "clown.blend"))
print("ACTIONS", [a.name for a in bpy.data.actions])
print("DONE")
