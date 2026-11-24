"""Pure-code quality gate for a scene module. Hard-fails (exit 1) on any violation; writes qa_report.json.

Usage:
  python qa.py --scene scenes/boy.py [--report qa_report.json] [--fps 24]
               [--width 720] [--height 1280] [--total-frames 96]

Checks every frame: NaN, floor penetration, rotation/position spikes,
camera framing, character size, and (optional) that the requested number of
frames really exists in the scene.
"""
import argparse
import collections
import importlib.util
import json
import math
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view

LIM = dict(
    floor_tol=0.03,        # m a foot may sink below floor
    max_speed=18.0,        # m/s any joint (limb tips in fast flips)
    max_accel=450.0,       # m/s^2 any joint (spike detector)
    max_rot_step=1.4,      # rad/frame per joint at 24 fps (~1900 deg/s, upper bound for a human limb)
    frame_margin=0.04,     # keypoints must be this far inside the frame (fraction)
    min_extent_frac=0.14,  # character bbox (larger side, in frame-height units) must be >= this
    slide_tol=0.012,       # m/frame planted foot may move
)

JOINT_NAMES = ("root", "torso", "head", "shoulder", "elbow", "hip", "knee", "ankle")
BONES = ("DEF-hips", "DEF-head", "DEF-foot.L", "DEF-foot.R", "DEF-hand.L", "DEF-hand.R")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", required=True)
    ap.add_argument("--report", default="qa_report.json")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--width", type=int, default=None, help="render width (default: scene value)")
    ap.add_argument("--height", type=int, default=None, help="render height (default: scene value)")
    ap.add_argument("--total-frames", type=int, default=None,
                    help="frames you plan to render; QA fails if the scene is shorter")
    return ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)


def main():
    a = parse_args()
    spec = importlib.util.spec_from_file_location("scene_mod", a.scene)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.build(bpy, a.fps)

    sc = bpy.context.scene
    cam = sc.camera
    if a.width:
        sc.render.resolution_x = a.width
    if a.height:
        sc.render.resolution_y = a.height

    errs, warns = [], []
    if cam is None:
        errs.append((0, "camera", "scene has no active camera"))
    if a.total_frames is not None and a.total_frames > sc.frame_end - sc.frame_start + 1:
        errs.append((0, "frames", f"requested {a.total_frames} frames but scene only has "
                                  f"{sc.frame_end - sc.frame_start + 1}"))

    J = {o.name + str(i): o for i, o in enumerate(bpy.data.objects)
         if o.type == "EMPTY" and o.name.split(".")[0] in JOINT_NAMES}
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    ankles = [o for k, o in J.items() if k.startswith("ankle")]
    key = [o for k, o in J.items() if k.startswith(("head", "ankle", "elbow"))]
    if not J and not arms:
        warns.append((0, "rig", "no joint empties or armature found: motion/framing checks skipped"))

    prev, prev2, prevrot = {}, {}, {}
    bounds = set(sc.get("clip_boundaries", []))   # frames where a clip starts/ends (hard cut, known pose pop)
    dt = 1.0 / a.fps
    sx, sy = sc.render.resolution_x, sc.render.resolution_y

    for f in range(sc.frame_start, sc.frame_end + 1):
        if cam is None:
            break
        sc.frame_set(f)
        bpy.context.view_layer.update()

        if arms and not J:                       # armature scenes (director): bone-based checks
            vis = False
            for ai, ao in enumerate(arms):
                for bn in BONES:
                    if bn not in ao.pose.bones:
                        errs.append((f, f"{ai}:{bn}", "missing bone"))
                        continue
                    pb = ao.pose.bones[bn]
                    p = ao.matrix_world @ pb.head
                    k = f"{ai}:{bn}"
                    if any(math.isnan(v) for v in p):
                        errs.append((f, k, "NaN"))
                        continue
                    if k in prev:
                        v = (p - prev[k]).length / dt
                        if v > LIM["max_speed"]:
                            errs.append((f, k, f"speed {v:.1f} m/s"))
                        if k in prev2:
                            acc = (p - 2 * prev[k] + prev2[k]).length / dt ** 2
                            if acc > LIM["max_accel"]:
                                (warns if any(abs(f - b) <= 2 for b in bounds) else errs).append(
                                    (f, k, f"accel spike {acc:.0f}"))
                    prev2[k] = prev.get(k, p)
                    prev[k] = p
                    if bn.startswith("DEF-foot") and p.z < -LIM["floor_tol"]:
                        errs.append((f, k, f"below floor z={p.z:.3f}"))
                    if bn == "DEF-head":
                        c = world_to_camera_view(sc, cam, p)
                        vis = vis or (0.02 <= c.x <= 0.98 and 0.02 <= c.y <= 0.98 and c.z > 0)
            if not vis:
                errs.append((f, "char", "no character head visible in frame"))
            continue

        for k, o in J.items():
            p = o.matrix_world.translation.copy()
            r = o.matrix_world.to_quaternion()
            if any(math.isnan(v) for v in (*p, *r)):
                errs.append((f, k, "NaN"))
                continue
            if k in prev:
                v = (p - prev[k]).length / dt
                if v > LIM["max_speed"]:
                    errs.append((f, k, f"speed {v:.1f} m/s"))
                if k in prev2:
                    acc = (p - 2 * prev[k] + prev2[k]).length / dt ** 2
                    if acc > LIM["max_accel"]:
                        errs.append((f, k, f"accel spike {acc:.0f}"))
                ang = r.rotation_difference(prevrot[k]).angle
                ang = min(ang, 2 * math.pi - ang)
                if ang > LIM["max_rot_step"]:
                    errs.append((f, k, f"rot jump {ang:.2f} rad"))
            prev2[k] = prev.get(k, p)
            prev[k] = p
            prevrot[k] = r
        for o in ankles:
            z = o.matrix_world.translation.z
            if z < -LIM["floor_tol"]:
                errs.append((f, o.name, f"below floor z={z:.3f}"))
        ys, xs = [], []
        for o in key:
            c = world_to_camera_view(sc, cam, o.matrix_world.translation)
            m = LIM["frame_margin"]
            if not (m <= c.x <= 1 - m and m <= c.y <= 1 - m and c.z > 0):
                errs.append((f, o.name, f"out of frame ({c.x:.2f},{c.y:.2f})"))
            ys.append(c.y)
            xs.append(c.x)
        if ys:
            ext = max(max(ys) - min(ys), (max(xs) - min(xs)) * sx / sy)
            if ext < LIM["min_extent_frac"]:
                errs.append((f, "char", f"too small in frame {ext:.2f}"))

    summ = collections.defaultdict(list)
    for fr, name, msg in errs:
        parts = msg.split()
        tail = parts[1] if parts[0] in ("rot", "accel", "too", "out", "below") and len(parts) > 1 else ""
        summ[name.split(".")[0].rstrip("0123456789") + ": " + parts[0] + " " + tail].append(fr)
    rep = {"scene": a.scene, "frames": sc.frame_end, "resolution": [sx, sy], "fps": a.fps,
           "errors": len(errs), "warnings_clip_cuts": len([w for w in warns if w[1] != "rig"]),
           "warnings_other": [list(w) for w in warns if w[1] == "rig"],
           "by_kind": {k: f"{len(v)} frames, {min(v)}..{max(v)}" for k, v in summ.items()},
           "first": [list(e) for e in errs[:20]]}
    with open(a.report, "w") as fh:
        json.dump(rep, fh, indent=1)
    print(json.dumps(rep, indent=1)[:2500])
    if errs:
        print(f"QA FAILED: {len(errs)} error(s)")
    else:
        print("QA PASSED")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
