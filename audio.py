
import argparse
import math
import os
import shutil
import subprocess
import tempfile
import wave
import struct

import numpy as np


def run(cmd):
    subprocess.run(cmd, check=True)


def make_music(path, duration, rate=44100):
    total = int(duration * rate)
    samples = np.zeros(total, dtype=np.float32)

    notes = [261.63, 329.63, 392.00, 523.25]
    for i in range(total):
        t = i / rate
        fade = min(1.0, t / 0.5, (duration - t) / 0.7)
        if fade < 0:
            fade = 0
        beat = int(t * 2) % len(notes)
        freq = notes[beat]
        samples[i] = (
            0.035 * math.sin(2 * math.pi * freq * t)
            + 0.012 * math.sin(2 * math.pi * freq * 2 * t)
        ) * max(0, fade)

    write_wav(path, samples, rate)


def make_effect(path, kind, duration=0.5, rate=44100):
    total = int(duration * rate)
    samples = np.zeros(total, dtype=np.float32)

    for i in range(total):
        t = i / rate
        progress = t / duration
        fade = (1 - progress) ** 2

        if kind == "boing":
            freq = 180 + 450 * progress
            value = math.sin(2 * math.pi * freq * t)
        else:
            freq = 700 - 450 * progress
            value = math.sin(2 * math.pi * freq * t)

        samples[i] = 0.22 * value * fade

    write_wav(path, samples, rate)


def write_wav(path, samples, rate):
    samples = np.clip(samples, -1, 1)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        data = b"".join(
            struct.pack("<h", int(x * 32767)) for x in samples
        )
        f.writeframes(data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", default="final.mp4")
    parser.add_argument(
        "--text",
        default="नमस्ते दोस्तों! हमारे वीडियो को देखिए।"
    )
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg is not installed")

    t = tempfile.mkdtemp()
    try:
        info = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            args.video
        ], text=True)
        duration = float(info.strip())

        music = os.path.join(t, "music.wav")
        boing = os.path.join(t, "boing.wav")
        whoosh = os.path.join(t, "whoosh.wav")
        voice = os.path.join(t, "voice.wav")

        make_music(music, duration)
        make_effect(boing, "boing")
        make_effect(whoosh, "whoosh")

        speaker = shutil.which("espeak-ng") or shutil.which("espeak")
        if not speaker:
            raise RuntimeError("Hindi voice engine espeak-ng missing")

        run([
            speaker, "-v", "hi", "-s", "145",
            "-w", voice, args.text
        ])

        run([
            "ffmpeg", "-y",
            "-i", args.video,
            "-i", voice,
            "-i", music,
            "-i", boing,
            "-i", whoosh,
            "-filter_complex",
            (
                "[1:a]adelay=200|200,volume=1.0[v];"
                "[2:a]volume=0.22[m];"
                "[3:a]adelay=900|900,volume=0.55[b];"
                "[4:a]adelay=2200|2200,volume=0.35[w];"
                "[v][m][b][w]amix=inputs=4:duration=longest,"
                "alimiter=limit=0.95[a]"
            ),
            "-map", "0:v:0",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            args.output
        ])

        print("SUCCESS:", args.output)

    finally:
        shutil.rmtree(t, ignore_errors=True)


if __name__ == "__main__":
    main()
