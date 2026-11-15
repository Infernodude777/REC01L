import bpy
import math
import os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "gun_clown.blend"))
if "GunClownRig" in bpy.data.objects:
    raise SystemExit("gun_clown.blend is already rigged - rebuild with build_gun_clown.py first")
scene = bpy.context.scene
scene.render.fps = 24

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

bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
arm = bpy.context.object
arm.name = "GunClownRig"
arm.data.name = "GunClownRig"
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
bone("head", (0, 0, 2.05), (0, 0, 3.70), "spine")
for s, sx in (("L", 1.0), ("R", -1.0)):
    a = ARM[s]
    bone("upper_arm." + s, a["shoulder"], a["elbow"], "spine")
    bone("forearm." + s, a["elbow"], a["wrist"], "upper_arm." + s)
    hand_tip = a["glove"] + (a["glove"] - a["wrist"]).normalized() * 0.22
    bone("hand." + s, a["wrist"], hand_tip, "forearm." + s)
    bone("thigh." + s, (sx * 0.25, 0, 1.02), (sx * 0.27, 0, 0.44), "hips")
    bone("foot." + s, (sx * 0.27, 0, 0.44), (sx * 0.29, -0.40, 0.13),
         "thigh." + s)
bpy.ops.object.mode_set(mode="OBJECT")
arm.show_in_front = True

HEAD_PARTS = ("Head", "Cheek", "Eye", "Pupil", "Brow", "Nose", "Lips", "Mouth",
              "Tooth", "Tongue", "Hair", "Curl", "Hat", "Brim", "Pompom")
SPINE_PARTS = ("Torso", "Collar", "Ruffle", "Bow", "Polka", "Button",
               "Shoulder puff", "Neck", "Bandolier", "Shell")
groups = {name: [] for name in (
    "head", "spine", "upper_arm.L", "upper_arm.R", "forearm.L", "forearm.R",
    "hand.L", "hand.R", "thigh.L", "thigh.R", "foot.L", "foot.R")}

for ob in [o for o in bpy.data.objects if o.type in ("MESH", "CURVE")]:
    if ob.name in ("Floor", "CamTarget", "AnimTarget", "Camera", "AnimCam"):
        continue
    n = ob.name
    side = "L" if ob.matrix_world.translation.x > 0 else "R"
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

act = new_action("Idle")
for f, a in ((1, 0), (13, 1.6), (25, 0), (37, 1.6), (49, 0)):
    kf("spine", f, rot=(a, 0, 0))
for f, a in ((1, -4), (25, 4), (49, -4)):
    kf("head", f, rot=(0, a, 0))
for s in ("L", "R"):
    for f, a in ((1, 0), (25, 1.4), (49, 0)):
        kf("upper_arm." + s, f, rot=(a, 0, 0))
stash(act)

act = new_action("Walk")
for f, a in ((1, -22), (7, 0), (13, 22), (19, 0), (25, -22)):
    kf("thigh.L", f, rot=(a, 0, 0))
for f, a in ((1, 22), (7, 0), (13, -22), (19, 0), (25, 22)):
    kf("thigh.R", f, rot=(a, 0, 0))
for f, a in ((1, 3), (7, 0), (13, -3), (19, 0), (25, 3)):
    kf("upper_arm.L", f, rot=(a, 0, 0))
for f, a in ((1, -3), (7, 0), (13, 3), (19, 0), (25, -3)):
    kf("upper_arm.R", f, rot=(a, 0, 0))
for f, a in ((1, 3), (13, -3), (25, 3)):
    kf("spine", f, rot=(0, a, 0))
for f, a in ((1, -2), (13, 2), (25, -2)):
    kf("head", f, rot=(0, a, 0))
stash(act)

act = new_action("Run")
for f, a in ((1, -38), (5, 0), (9, 38), (13, 0), (17, -38)):
    kf("thigh.L", f, rot=(a, 0, 0))
for f, a in ((1, 38), (5, 0), (9, -38), (13, 0), (17, 38)):
    kf("thigh.R", f, rot=(a, 0, 0))
for f, a in ((1, 4), (5, 0), (9, -4), (13, 0), (17, 4)):
    kf("upper_arm.L", f, rot=(a, 0, 0))
for f, a in ((1, -4), (5, 0), (9, 4), (13, 0), (17, -4)):
    kf("upper_arm.R", f, rot=(a, 0, 0))
kf("spine", 1, rot=(10, 0, 0))
kf("spine", 17, rot=(10, 0, 0))
kf("head", 1, rot=(-8, 0, 0))
kf("head", 17, rot=(-8, 0, 0))
stash(act)

act = new_action("Aim")
for f, a in ((1, 0), (15, 1.2), (30, 0)):
    kf("spine", f, rot=(a, 0, 0))
for s in ("L", "R"):
    for f, a in ((1, 0), (15, -1.6), (30, 0)):
        kf("upper_arm." + s, f, rot=(a, 0, 0))
    for f, a in ((1, 0), (15, 1.0), (30, 0)):
        kf("forearm." + s, f, rot=(a, 0, 0))
for f, a in ((1, 0), (15, -1.5), (30, 0)):
    kf("head", f, rot=(a, 0, 0))
stash(act)

act = new_action("Die")
okf(4, rot=(-6, 0, 0))
okf(9, rot=(-20, 0, 0))
okf(20, rot=(-52, 0, 0), loc=(0, 0, 0.10))
okf(24, rot=(-58, 0, 0), loc=(0, 0, 0.12))
okf(30, rot=(-58, 0, 0), loc=(0, 0, 0.12))
kf("upper_arm.L", 6, rot=(-30, 0, 24))
kf("upper_arm.L", 20, rot=(-58, 0, 18))
kf("upper_arm.L", 30, rot=(-62, 0, 16))
kf("upper_arm.R", 6, rot=(-30, 0, -24))
kf("upper_arm.R", 20, rot=(-58, 0, -18))
kf("upper_arm.R", 30, rot=(-62, 0, -16))
for s in ("L", "R"):
    kf("forearm." + s, 6, rot=(-18, 0, 0))
    kf("forearm." + s, 30, rot=(-10, 0, 0))
    kf("thigh." + s, 20, rot=(20, 0, 0))
    kf("thigh." + s, 30, rot=(24, 0, 0))
kf("spine", 4, rot=(-8, 0, 0))
kf("spine", 12, rot=(-16, 0, 0))
kf("spine", 20, rot=(6, 0, 0))
kf("spine", 30, rot=(4, 0, 0))
kf("head", 6, rot=(-14, 0, 0))
kf("head", 20, rot=(14, 0, 0))
kf("head", 30, rot=(10, 0, 0))
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

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "gun_clown.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE, "gun_clown.glb"),
                          export_format="GLB", export_animations=True)

checks = (("Idle", 1, "gun_idle"), ("Aim", 16, "gun_aim"),
          ("Walk", 13, "gun_walk"), ("Die", 24, "gun_die"))
for act_name, frame, label in checks:
    reset_pose()
    act = bpy.data.actions[act_name]
    arm.animation_data.action = act
    scene.frame_set(frame)
    scene.render.filepath = os.path.join(HERE, "pose_%s.png" % label)
    try:
        bpy.ops.render.render(write_still=True)
    except Exception as exc:
        print("RENDER SKIPPED", exc)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "gun_clown.blend"))
print("ACTIONS", [a.name for a in bpy.data.actions])
print("DONE")
