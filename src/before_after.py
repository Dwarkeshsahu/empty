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
A segment may add "zoom": 1.35 and "focus": [cx, cy] to punch in on the subject.
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
        dur = seg["end"] - seg["start"]
        total += dur
        cmd += ["-ss", str(seg["start"]), "-t", f"{dur:.3f}", "-i", seg["src"]]
        chain = ["setpts=PTS-STARTPTS"]
        # optional punch-in: zoom factor + where to aim (0..1 of the free margin)
        z = seg.get("zoom", 1.0)
        if z > 1.0:
            cx, cy = seg.get("focus", [0.5, 0.5])
            chain.append(f"crop=iw/{z}:ih/{z}:(iw-ow)*{cx}:(ih-oh)*{cy}")
        chain += [
            f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos",
            f"crop={W}:{H}",
            f"fps={FPS}",
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
