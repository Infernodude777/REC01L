
import bpy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "clown.blend"))
scene = bpy.context.scene
arm = bpy.data.objects["ClownRig"]
ENDS = {"Walk": 24, "Run": 16, "Aim": 30, "Die": 30, "Idle": 48}

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(ENDS)
scene.render.resolution_x = 360
scene.render.resolution_y = 360
try:
    scene.eevee.taa_render_samples = 8
except AttributeError:
    pass
scene.render.image_settings.file_format = "PNG"

for name in args:
    out = os.path.join(HERE, "clip_frames", name)
    os.makedirs(out, exist_ok=True)
    for pb in arm.pose.bones:
        pb.rotation_euler = (0, 0, 0)
        pb.location = (0, 0, 0)
    arm.rotation_euler = (0, 0, 0)
    arm.location = (0, 0, 0)
    arm.animation_data.action = bpy.data.actions[name]
    for f in range(1, ENDS[name] + 1):
        scene.frame_set(f)
        scene.render.filepath = os.path.join(out, "f%03d.png" % f)
        bpy.ops.render.render(write_still=True)
    print("CLIPDONE", name)
print("ALLDONE")
