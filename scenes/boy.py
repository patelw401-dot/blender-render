import bpy
import math
from mathutils import Vector

def build(bpy, fps):
bpy.ops.wm.read_factory_settings(use_empty=True)

sc = bpy.context.scene
sc.frame_start = 1
sc.frame_end = fps * 4

# Vertical Shorts format
sc.render.resolution_x = 720
sc.render.resolution_y = 1280
sc.render.resolution_percentage = 100

def material(name, color):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    return m

skin = material("Skin", (0.95, 0.62, 0.42))
blue = material("Blue Shirt", (0.05, 0.25, 0.85))
black = material("Hair", (0.025, 0.02, 0.04))
white = material("Eyes", (1, 1, 1))
green = material("Ground", (0.12, 0.4, 0.18))
shoe = material("Shoes", (0.03, 0.03, 0.04))

def sphere(name, loc, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=24,
        ring_count=16,
        location=loc
    )
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return obj

def marker(name, loc):
    obj = bpy.data.objects.new(name, None)
    sc.collection.objects.link(obj)
    obj.location = loc
    return obj

# Ground
bpy.ops.mesh.primitive_plane_add(size=200)
ground = bpy.context.object
ground.name = "Ground"
ground.data.materials.append(green)

# Cartoon body
body = sphere(
    "Body",
    (0, 0, 1.25),
    (0.48, 0.30, 0.62),
    blue
)

head = sphere(
    "Head",
    (0, 0, 2.15),
    (0.52, 0.46, 0.56),
    skin
)

sphere(
    "Hair",
    (0, 0.06, 2.48),
    (0.54, 0.47, 0.27),
    black
)

# Eyes and pupils
for x in (-0.19, 0.19):
    sphere(
        "Eye",
        (x, -0.415, 2.20),
        (0.075, 0.055, 0.10),
        white
    )

    sphere(
        "Pupil",
        (x, -0.465, 2.20),
        (0.035, 0.025, 0.055),
        black
    )

# Smile
sphere(
    "Smile",
    (0, -0.445, 2.00),
    (0.13, 0.025, 0.035),
    black
)

# Arms
arm_l = sphere(
    "LeftArm",
    (-0.58, 0, 1.60),
    (0.15, 0.15, 0.43),
    skin
)

arm_r = sphere(
    "RightArm",
    (0.58, 0, 1.60),
    (0.15, 0.15, 0.43),
    skin
)

arm_r.rotation_euler[1] = -0.5

# Legs and shoes
for x in (-0.22, 0.22):
    sphere(
        "Leg",
        (x, 0, 0.48),
        (0.17, 0.18, 0.43),
        black
    )

    sphere(
        "Shoe",
        (x, -0.08, 0.10),
        (0.20, 0.29, 0.10),
        shoe
    )

# QA markers
marker("root", (0, 0, 0.10))
marker("torso", (0, 0, 1.25))
marker("head", (0, 0, 2.15))

marker("shoulder.L", (-0.45, 0, 1.75))
marker("shoulder.R", (0.45, 0, 1.75))

marker("elbow.L", (-0.65, 0, 1.60))
elbow_r = marker("elbow.R", (0.65, 0, 1.60))

marker("hip.L", (-0.22, 0, 0.85))
marker("hip.R", (0.22, 0, 0.85))

marker("knee.L", (-0.22, 0, 0.45))
marker("knee.R", (0.22, 0, 0.45))

marker("ankle.L", (-0.22, 0, 0.10))
marker("ankle.R", (0.22, 0, 0.10))

# Waving animation
for f in range(1, sc.frame_end + 1, 3):
    wave = math.sin(f * 0.12)

    arm_r.rotation_euler[1] = -0.5 + 0.35 * wave
    arm_r.keyframe_insert(
        data_path="rotation_euler",
        frame=f
    )

    elbow_r.location.z = 1.60 + 0.08 * wave
    elbow_r.keyframe_insert(
        data_path="location",
        frame=f
    )

    body.location.z = 1.25 + 0.04 * abs(wave)
    body.keyframe_insert(
        data_path="location",
        frame=f
    )

# Lighting
bpy.ops.object.light_add(
    type="AREA",
    location=(0, -5, 6)
)

light = bpy.context.object
light.name = "KeyLight"
light.data.energy = 500
light.data.shape = "DISK"
light.data.size = 5

# Camera
cam_data = bpy.data.cameras.new("Camera")
cam = bpy.data.objects.new("Camera", cam_data)
sc.collection.objects.link(cam)

cam.location = (0, -9, 2.2)

target = Vector((0, 0, 1.3))
direction = target - cam.location

cam.rotation_euler = direction.to_track_quat(
    "-Z",
    "Y"
).to_euler()

# Wider lens for safer QA framing
cam.data.lens = 40
cam.data.clip_start = 0.1
cam.data.clip_end = 100

sc.camera = cam

# Background
world = bpy.data.worlds.new("World")
world.use_nodes = True

world.node_tree.nodes["Background"].inputs[0].default_value = (
    0.3,
    0.4,
    0.65,
    1
)

world.node_tree.nodes["Background"].inputs[1].default_value = 0.8

sc.world = world

# Keep the first frame ready for render/QA
sc.frame_set(1)
