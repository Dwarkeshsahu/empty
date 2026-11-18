"""Build a "I went from THIS -> To THIS" reel from a JSON spec using ffmpeg.

Usage:
    python src/before_after.py projects/surf_01.json

Spec format (times in seconds, relative to the source clip or to the segment):
{
  "output": "videos/output/surf_01.mp4",
  "font": "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
  "grade": "eq=brightness=0.04:contrast=1.08:saturation=1.2",
  "audio": null,                      # optional music file; null = silent track
  "segments": [
    {"src": "path.mp4", "start": 1.0, "end": 3.9,
     "texts": [{"text": "I", "t0": 0.0, "t1": 1.0, "x": 0.2, "y": 0.16, "size": 64}]}
  ]
}
x / y are fractions of the frame (x may be "center"); size is px at 1080 wide.
Optional per segment:
  "speed": 0.5        slow motion (0.5 is smooth for 60 fps footage), 2.0 = double speed
  "zoom": 1.35        static punch-in, or [1.0, 1.4] to zoom in / [1.4, 1.0] to zoom out
  "focus": [cx, cy]   where the zoom aims, 0..1 across the frame (default centre)
Speed ramps: list the same clip as consecutive segments with different speeds.
Text t0/t1 are in reel time, i.e. after the speed change.
"""

import json
import subprocess
import sys
from pathlib import Path

import config


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def drawtext(t: dict, font: str) -> str:
    x = "(w-text_w)/2" if t.get("x", "center") == "center" else f"w*{t['x']}"
    y = f"h*{t['y']}"
    size = t.get("size", 96)
    return (
        f"drawtext=fontfile='{font}':text='{esc(t['text'])}':fontsize={size}"
        f":fontcolor=white:borderw={max(2, size // 22)}:bordercolor=black@0.9"
        f":shadowx=0:shadowy=3:shadowcolor=black@0.35"
        f":x={x}:y={y}:enable='between(t,{t['t0']},{t['t1']})'"
    )


def build(spec: dict) -> list[str]:
    W, H, FPS = config.WIDTH, config.HEIGHT, config.FPS
    font = spec["font"]
    grade = spec.get("grade")
    cmd = ["ffmpeg", "-y", "-v", "error", "-stats"]
    filters, labels = [], []
    total = 0.0

    for i, seg in enumerate(spec["segments"]):
        src_dur = seg["end"] - seg["start"]
        speed = seg.get("speed", 1.0)
        dur = src_dur / speed  # length in the finished reel
        total += dur
        cmd += ["-ss", str(seg["start"]), "-t", f"{src_dur:.3f}", "-i", seg["src"]]

        # zoom: a number (static) or [from, to] (animated, eased over the segment)
        z = seg.get("zoom", 1.0)
        z0, z1 = (z, z) if isinstance(z, (int, float)) else z
        ease = f"(0.5-0.5*cos(PI*clip(t/{dur:.3f},0,1)))"
        zexpr = f"({z0}+({z1}-{z0})*{ease})" if z0 != z1 else str(z0)
        cx, cy = seg.get("focus", [0.5, 0.5])

        chain = [
            f"setpts=(PTS-STARTPTS)/{speed}",  # <1 = slow motion, >1 = fast
            f"fps={FPS}",
            "crop='min(iw,ih*9/16)':'min(ih,iw*16/9)'",  # force 9:16
            f"scale=w='trunc({W}*{zexpr}/2)*2':h='trunc({H}*{zexpr}/2)*2'"
            f":eval=frame:flags=lanczos",
            f"crop={W}:{H}:x='(iw-ow)*{cx}':y='(ih-oh)*{cy}'",
        ]
        if grade:
            chain.append(grade)
        chain += [drawtext(t, font) for t in seg.get("texts", [])]
        chain += ["format=yuv420p", "setsar=1"]
        filters.append(f"[{i}:v:0]{','.join(chain)}[v{i}]")
        labels.append(f"[v{i}]")

    n = len(spec["segments"])
    filters.append(f"{''.join(labels)}concat=n={n}:v=1:a=0[vout]")

    if spec.get("audio"):
        cmd += ["-i", spec["audio"]]
        filters.append(f"[{n}:a]atrim=0:{total:.3f},afade=t=out:st={total - 0.6:.3f}:d=0.6[aout]")
    else:
        cmd += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
        filters.append(f"[{n}:a]anull[aout]")

    cmd += [
        "-filter_complex", ";".join(filters),
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", config.CODEC, "-preset", "slow", "-crf", "21", "-maxrate", "14M", "-bufsize", "28M",
        "-pix_fmt", config.PIXEL_FORMAT, "-profile:v", "high",
        "-c:a", config.AUDIO_CODEC, "-b:a", "192k",
        "-movflags", "+faststart", "-shortest",
        spec["output"],
    ]
    return cmd


def main() -> None:
    spec = json.loads(Path(sys.argv[1]).read_text())
    Path(spec["output"]).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(build(spec), check=True)
    print(f"Wrote {spec['output']}")


if __name__ == "__main__":
    main()
