"""Cartoon boy waving at the camera (vertical 720x1280 Shorts scene).

Interface used by render.py and qa.py:  build(bpy, fps)

The character is a small joint rig made of Empties. All the meshes are
parented to those joints, so the QA system (qa.py) can track the joints
named root / torso / head / shoulder / elbow / hip / knee / ankle.
Z is up, the boy faces -Y (towards the camera).
"""
import math

import bpy as _bpy_module  # noqa: F401  (build() receives bpy as an argument too)
from mathutils import Matrix, Vector

WIDTH = 720
HEIGHT = 1280
DURATION_SECONDS = 4


def smoothstep(a, b, x):
    """0 below a, 1 above b, smooth in between."""
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    t = (x - a) / (b - a)
    return t * t * (3.0 - 2.0 * t)


def build(bpy, fps):
    bpy.ops.wm.read_factory_settings(use_empty=True)

    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = int(fps * DURATION_SECONDS)
    sc.render.fps = fps
    sc.render.fps_base = 1.0
    sc.render.resolution_x = WIDTH
    sc.render.resolution_y = HEIGHT
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "Standard"

    # ------------------------------------------------------------------
    # Materials
    # ------------------------------------------------------------------
    def material(name, color, roughness=0.55):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        m.diffuse_color = (*color, 1.0)
        return m

    skin = material("Skin", (0.78, 0.43, 0.29), 0.5)
    skin_dark = material("SkinDark", (0.62, 0.30, 0.20), 0.5)
    blush = material("Blush", (0.85, 0.28, 0.25), 0.6)
    shirt = material("Shirt", (0.03, 0.22, 0.85), 0.6)
    stripe = material("ShirtStripe", (0.95, 0.75, 0.05), 0.6)
    shorts = material("Shorts", (0.36, 0.24, 0.10), 0.7)
    hair_m = material("Hair", (0.045, 0.025, 0.015), 0.45)
    white = material("White", (0.95, 0.95, 0.95), 0.3)
    iris = material("Iris", (0.10, 0.045, 0.02), 0.2)
    black = material("Black", (0.01, 0.01, 0.012), 0.2)
    mouth_m = material("Mouth", (0.35, 0.04, 0.04), 0.4)
    sock = material("Sock", (0.9, 0.9, 0.9), 0.8)
    shoe = material("Shoe", (0.75, 0.05, 0.04), 0.5)
    sole = material("Sole", (0.9, 0.9, 0.88), 0.6)
    grass = material("Grass", (0.10, 0.42, 0.12), 0.9)
    plat = material("Platform", (0.80, 0.62, 0.35), 0.8)

    # ------------------------------------------------------------------
    # Joint rig (empties).  Parents have no rotation/scale while building,
    # so a child's local offset is simply (world - parent_world).
    # ------------------------------------------------------------------
    jpos = {}
    jobj = {}

    def joint(name, world, parent=None):
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "SPHERE"
        e.empty_display_size = 0.03
        sc.collection.objects.link(e)
        world = Vector(world)
        if parent is None:
            e.location = world
        else:
            e.parent = jobj[parent]
            e.location = world - jpos[parent]
        jpos[name] = world
        jobj[name] = e
        return e

    joint("root", (0, 0, 0.10))
    joint("torso", (0, 0, 0.90), "root")
    joint("head", (0, 0, 1.27), "torso")
    joint("shoulder.L", (-0.25, 0, 1.09), "torso")
    joint("shoulder.R", (0.25, 0, 1.09), "torso")
    joint("elbow.L", (-0.31, 0, 0.87), "shoulder.L")
    joint("elbow.R", (0.31, 0, 0.87), "shoulder.R")
    joint("hip.L", (-0.10, 0, 0.70), "root")
    joint("hip.R", (0.10, 0, 0.70), "root")
    joint("knee.L", (-0.10, 0, 0.40), "hip.L")
    joint("knee.R", (0.10, 0, 0.40), "hip.R")
    joint("ankle.L", (-0.10, 0, 0.10), "knee.L")
    joint("ankle.R", (0.10, 0, 0.10), "knee.R")

    # ------------------------------------------------------------------
    # Mesh helpers
    # ------------------------------------------------------------------
    def attach(obj, joint_name):
        obj.parent = jobj[joint_name]
        obj.matrix_parent_inverse = Matrix.Translation(-jpos[joint_name])

    def sphere(name, center, scale, mat, joint_name, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=32, ring_count=16, radius=1.0, location=center)
        o = bpy.context.object
        o.name = name
        o.scale = scale
        o.rotation_euler = rot
        o.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        attach(o, joint_name)
        return o

    def tube(name, p0, p1, radius, mat, joint_name, caps=True):
        """Capsule-like limb between two world points."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=32, radius=radius, depth=d.length, location=(p0 + p1) / 2)
        o = bpy.context.object
        o.name = name
        o.rotation_euler = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
        o.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        attach(o, joint_name)
        if caps:
            sphere(name + "_capA", p0, (radius,) * 3, mat, joint_name)
            sphere(name + "_capB", p1, (radius,) * 3, mat, joint_name)
        return o

    # ------------------------------------------------------------------
    # Environment: grass, round platform
    # ------------------------------------------------------------------
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, -0.05))
    ground = bpy.context.object
    ground.name = "Ground"
    ground.data.materials.append(grass)

    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.5, depth=0.05,
                                        location=(0, 0, -0.025))
    pl = bpy.context.object
    pl.name = "Platform"
    pl.data.materials.append(plat)
    bpy.ops.object.shade_smooth()

    # ------------------------------------------------------------------
    # Torso, neck, shorts
    # ------------------------------------------------------------------
    sphere("Shirt", (0, 0, 0.94), (0.215, 0.145, 0.25), shirt, "torso")
    sphere("ShirtStripe", (0, 0, 0.95), (0.222, 0.150, 0.045), stripe, "torso")
    sphere("Shorts", (0, 0, 0.75), (0.225, 0.155, 0.13), shorts, "torso")
    tube("Neck", (0, 0, 1.12), (0, 0, 1.30), 0.06, skin, "torso", caps=False)
    sphere("Collar", (0, 0, 1.13), (0.115, 0.095, 0.045), shirt, "torso")

    # ------------------------------------------------------------------
    # Head
    # ------------------------------------------------------------------
    sphere("Head", (0, 0, 1.50), (0.295, 0.275, 0.285), skin, "head")
    for sx in (-1, 1):
        sphere("Ear", (sx * 0.285, 0.0, 1.47), (0.045, 0.05, 0.07), skin, "head")
        sphere("EarInner", (sx * 0.292, -0.012, 1.47), (0.025, 0.03, 0.045),
               skin_dark, "head")
        sphere("Cheek", (sx * 0.17, -0.235, 1.43), (0.06, 0.02, 0.04), blush, "head")

    eye_parts = []  # parts that squash for blinking: (object, base_scale_z)
    for sx in (-1, 1):
        for name, loc, scl, mat in (
            ("EyeWhite", (sx * 0.105, -0.232, 1.53), (0.060, 0.032, 0.075), white),
            ("EyeIris", (sx * 0.105, -0.258, 1.53), (0.040, 0.020, 0.052), iris),
            ("EyePupil", (sx * 0.105, -0.268, 1.53), (0.022, 0.012, 0.030), black),
            ("EyeShine", (sx * 0.093, -0.274, 1.553), (0.011, 0.006, 0.014), white),
        ):
            o = sphere(name, loc, scl, mat, "head")
            eye_parts.append((o, scl[2]))
        sphere("Brow", (sx * 0.105, -0.236, 1.618), (0.060, 0.016, 0.014), hair_m,
               "head", rot=(0, sx * math.radians(-10), 0))

    sphere("Nose", (0, -0.272, 1.455), (0.030, 0.026, 0.026), skin_dark, "head")

    # Smile: small dark spheres along an arc
    for i in range(9):
        a = math.radians(-50 + i * 12.5)
        x = math.sin(a) * 0.085
        z = 1.385 - math.cos(a) * 0.035 + 0.035
        sphere("Smile", (x, -0.262 + abs(x) * 0.25, z), (0.0085, 0.008, 0.0085),
               mouth_m, "head")

    # Hair: cap + fringe + tuft
    sphere("HairCap", (0, 0.045, 1.585), (0.312, 0.285, 0.255), hair_m, "head")
    for i, x in enumerate((-0.17, -0.085, 0.0, 0.085, 0.17)):
        sphere("Fringe", (x, -0.205, 1.675 - 0.012 * abs(i - 2)),
               (0.075, 0.060, 0.050), hair_m, "head",
               rot=(0, math.radians((i - 2) * 12), 0))
    sphere("Tuft", (0.03, -0.02, 1.84), (0.07, 0.06, 0.07), hair_m, "head")

    # ------------------------------------------------------------------
    # Arms (sleeve on the upper arm, skin on the forearm, round hand)
    # ------------------------------------------------------------------
    for sx, side in ((-1, "L"), (1, "R")):
        sh = (sx * 0.25, 0, 1.09)
        el = (sx * 0.31, 0, 0.87)
        wr = (sx * 0.335, -0.015, 0.66)
        sphere("ShoulderBall." + side, sh, (0.085, 0.085, 0.085), shirt, "shoulder." + side)
        tube("Sleeve." + side, sh, (sx * 0.295, 0, 0.93), 0.075, shirt, "shoulder." + side,
             caps=False)
        tube("UpperArm." + side, (sx * 0.295, 0, 0.93), el, 0.052, skin,
             "shoulder." + side)
        tube("Forearm." + side, el, wr, 0.050, skin, "elbow." + side)
        sphere("Hand." + side, (wr[0], wr[1] - 0.005, wr[2] - 0.05), (0.068, 0.045, 0.075),
               skin, "elbow." + side)
        sphere("Thumb." + side, (wr[0] - sx * 0.055, wr[1] - 0.025, wr[2] - 0.035),
               (0.022, 0.022, 0.04), skin, "elbow." + side,
               rot=(0, sx * math.radians(25), 0))

    # ------------------------------------------------------------------
    # Legs: thigh, shorts leg, shin, sock, shoe
    # ------------------------------------------------------------------
    for sx, side in ((-1, "L"), (1, "R")):
        hp = (sx * 0.10, 0, 0.70)
        kn = (sx * 0.10, 0, 0.40)
        an = (sx * 0.10, 0, 0.10)
        tube("Thigh." + side, hp, kn, 0.065, skin, "hip." + side)
        tube("ShortsLeg." + side, (sx * 0.10, 0, 0.74), (sx * 0.10, 0, 0.52), 0.098,
             shorts, "hip." + side)
        tube("Shin." + side, kn, (sx * 0.10, 0, 0.22), 0.055, skin, "knee." + side)
        tube("Sock." + side, (sx * 0.10, 0, 0.26), (sx * 0.10, 0, 0.12), 0.062, sock,
             "knee." + side, caps=False)
        sphere("Shoe." + side, (sx * 0.10, -0.04, 0.075), (0.085, 0.165, 0.075), shoe,
               "ankle." + side)
        sphere("Sole." + side, (sx * 0.10, -0.04, 0.025), (0.088, 0.170, 0.028), sole,
               "ankle." + side)

    # ------------------------------------------------------------------
    # Lights, camera, sky
    # ------------------------------------------------------------------
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(50), 0, math.radians(-30)))
    sun = bpy.context.object
    sun.name = "Sun"
    sun.data.energy = 3.0
    sun.data.angle = math.radians(6)

    bpy.ops.object.light_add(type="AREA", location=(1.5, -4.0, 2.2))
    fill = bpy.context.object
    fill.name = "FillLight"
    fill.data.energy = 120
    fill.data.size = 4
    fill.rotation_euler = (Vector((0, 0, 0.9)) - fill.location).to_track_quat("-Z", "Y").to_euler()

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 38
    cam_data.sensor_fit = "VERTICAL"
    cam_data.sensor_height = 36
    cam_data.clip_start = 0.1
    cam_data.clip_end = 100
    cam = bpy.data.objects.new("Camera", cam_data)
    sc.collection.objects.link(cam)
    cam.location = (0, -3.5, 0.95)
    cam.rotation_euler = (Vector((0, 0, 0.92)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes["Background"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0.75, 0.88, 0.95, 1)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (0.20, 0.45, 0.85, 1)
    bg.inputs["Strength"].default_value = 1.0
    sc.world = world

    # ------------------------------------------------------------------
    # Animation: idle breathing + friendly wave with the right hand
    # ------------------------------------------------------------------
    torso = jobj["torso"]
    head = jobj["head"]
    sh_r = jobj["shoulder.R"]
    el_r = jobj["elbow.R"]
    sh_l = jobj["shoulder.L"]

    for f in range(sc.frame_start, sc.frame_end + 1):
        t = (f - 1) / float(fps)

        # 0 = arm down, 1 = arm raised; up at ~0.3-1.0 s, down at ~3.1-3.8 s
        raised = smoothstep(0.3, 1.0, t) - smoothstep(3.1, 3.8, t)
        wave = math.sin(2 * math.pi * 2.2 * t)

        sh_r.rotation_euler = (0, -2.0 * raised, 0)
        sh_r.keyframe_insert(data_path="rotation_euler", frame=f)

        el_r.rotation_euler = (0, -(0.75 + 0.40 * wave) * raised, 0)
        el_r.keyframe_insert(data_path="rotation_euler", frame=f)

        sh_l.rotation_euler = (0, 0.04 * math.sin(2 * math.pi * 0.5 * t), 0)
        sh_l.keyframe_insert(data_path="rotation_euler", frame=f)

        torso.location = (0, 0, 0.90 + 0.008 * math.sin(2 * math.pi * 1.0 * t)
                          + 0.010 * abs(wave) * raised)
        torso.rotation_euler = (0, 0.02 * raised, 0.03 * math.sin(2 * math.pi * 0.5 * t))
        torso.keyframe_insert(data_path="location", frame=f)
        torso.keyframe_insert(data_path="rotation_euler", frame=f)

        head.rotation_euler = (0.03 * math.sin(2 * math.pi * 0.8 * t),
                               -0.10 * raised + 0.03 * math.sin(2 * math.pi * 0.5 * t),
                               0.05 * math.sin(2 * math.pi * 0.4 * t))
        head.keyframe_insert(data_path="rotation_euler", frame=f)

        # blinks around 1.4 s and 2.9 s (0.2 s long)
        blink = 0.0
        for t0 in (1.4, 2.9):
            blink = max(blink, math.sin(math.pi * min(max((t - t0) / 0.2, 0.0), 1.0)))
        for o, base_z in eye_parts:
            o.scale[2] = base_z * (1.0 - 0.9 * blink)
            o.keyframe_insert(data_path="scale", index=2, frame=f)

    sc.frame_set(sc.frame_start)
