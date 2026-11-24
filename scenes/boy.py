
import bpy
import math

def build(bpy, fps):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = fps * 4

    def mat(name, color):
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*color, 1)
        return m

    skin = mat("Skin", (0.95, 0.62, 0.42))
    blue = mat("Blue Shirt", (0.05, 0.25, 0.85))
    black = mat("Black Hair", (0.025, 0.02, 0.04))
    white = mat("Eyes", (1, 1, 1))
    ground = mat("Ground", (0.12, 0.55, 0.25))

    def sphere(name, loc, scale, material):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, location=loc)
        o = bpy.context.object
        o.name = name
        o.scale = scale
        o.data.materials.append(material)
        bpy.ops.object.shade_smooth()
        return o

    bpy.ops.mesh.primitive_plane_add(size=200)
    bpy.context.object.data.materials.append(ground)

    body = sphere("Body", (0, 0, 1.25), (0.48, 0.3, 0.65), blue)
    head = sphere("Head", (0, 0, 2.15), (0.55, 0.48, 0.58), skin)
    sphere("Hair", (0, 0.08, 2.52), (0.55, 0.48, 0.28), black)

    for x in (-0.2, 0.2):
        sphere("Eye", (x, -0.43, 2.22), (0.09, 0.06, 0.12), white)

    arm = sphere("WavingArm", (0.62, 0, 1.65), (0.16, 0.16, 0.48), skin)
    arm.rotation_euler[1] = -0.7

    for x in (-0.22, 0.22):
        sphere("Leg", (x, 0, 0.48), (0.17, 0.18, 0.48), black)

    for f in range(1, sc.frame_end + 1, 3):
        arm.rotation_euler[1] = -0.7 + 0.6 * math.sin(f * 0.35)
        arm.keyframe_insert(data_path="rotation_euler", frame=f)
        body.location.z = 1.25 + 0.06 * abs(math.sin(f * 0.25))
        body.keyframe_insert(data_path="location", frame=f)

    bpy.ops.object.light_add(type="AREA", location=(0, -5, 6))
    bpy.context.object.data.energy = 500
    bpy.context.object.data.shape = "DISK"
    bpy.context.object.data.size = 5

    cam_data = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cam_data)
    sc.collection.objects.link(cam)
    cam.location = (4, -8, 3.2)
    cam.rotation_euler = (math.radians(72), 0, math.radians(25))
    cam.data.lens = 50
    sc.camera = cam

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.3, 0.4, 0.65, 1)
    sc.world = world
  
