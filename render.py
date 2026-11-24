"""Headless Blender frame-range renderer (bpy module, Cycles CPU).

Usage:
  python render.py --start 1 --end 120 --step 2 --out frames
Defaults: scenes/boy.py, 720x1280 (vertical Shorts), 24 fps.
Hard-fails if any expected frame is missing after render.
"""
import argparse
import importlib.util
import os
import sys
import time

import bpy


def load_scene_module(path):
    if not os.path.isfile(path):
        sys.exit(f"FATAL: scene file not found: {path}")
    spec = importlib.util.spec_from_file_location("scene_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scene", default="scenes/boy.py")
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--end", type=int, required=True)
    p.add_argument("--step", type=int, default=1)
    p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=720)
    p.add_argument("--height", type=int, default=1280)
    p.add_argument("--samples", type=int, default=24)
    p.add_argument("--fps", type=int, default=24)
    a = p.parse_args()

    if a.step < 1 or a.start < 1 or a.end < a.start:
        sys.exit("FATAL: need start >= 1, end >= start, step >= 1")

    os.makedirs(a.out, exist_ok=True)
    mod = load_scene_module(a.scene)
    if not hasattr(mod, "build"):
        sys.exit(f"FATAL: {a.scene} has no build(bpy, fps) function")
    mod.build(bpy, a.fps)

    sc = bpy.context.scene
    if a.end > sc.frame_end:
        sys.exit(f"FATAL: --end {a.end} is beyond the scene's last frame {sc.frame_end}")
    if sc.camera is None:
        sys.exit("FATAL: scene has no active camera")

    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        print("WARNING: OpenImageDenoise not available, using default denoiser", flush=True)
    sc.render.resolution_x = a.width
    sc.render.resolution_y = a.height
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.fps = a.fps
    sc.render.threads_mode = "AUTO"

    frames = list(range(a.start, a.end + 1, a.step))
    t0 = time.time()
    for i, f in enumerate(frames, 1):
        sc.frame_set(f)
        path = os.path.abspath(os.path.join(a.out, f"frame_{f:06d}.png"))
        sc.render.filepath = path
        t = time.time()
        bpy.ops.render.render(write_still=True)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            sys.exit(f"FATAL: frame {f} was not written: {path}")
        print(f"frame {f} ({i}/{len(frames)}) {time.time() - t:.1f}s", flush=True)

    got = len([x for x in os.listdir(a.out) if x.endswith(".png")])
    if got != len(frames):
        sys.exit(f"FATAL: expected {len(frames)} frames, found {got}")
    print(f"done {len(frames)} frames in {time.time() - t0:.1f}s "
          f"({(time.time() - t0) / len(frames):.1f}s/frame)")


if __name__ == "__main__":
    main()
