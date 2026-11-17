"""Render a simple text-on-gradient reel as a starting template."""

import argparse
from pathlib import Path

import numpy as np
from moviepy import VideoClip

import config


def gradient_frame(t: float, duration: float) -> np.ndarray:
    """Vertical gradient whose colours shift over time."""
    phase = t / duration
    y = np.linspace(0, 1, config.HEIGHT)[:, None]
    r = (40 + 180 * y * (1 - phase)) * np.ones((1, config.WIDTH))
    g = (20 + 100 * phase) * np.ones((config.HEIGHT, config.WIDTH))
    b = (120 + 120 * (1 - y) * phase) * np.ones((1, config.WIDTH))
    return np.dstack([r, g, b]).clip(0, 255).astype("uint8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", default="Hello Reels")
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--out", default="videos/output/reel.mp4")
    args = parser.parse_args()

    duration = min(args.duration, config.MAX_DURATION)
    clip = VideoClip(lambda t: gradient_frame(t, duration), duration=duration)

    try:
        from moviepy import CompositeVideoClip, TextClip

        text = (
            TextClip(text=args.text, font_size=96, color="white",
                     size=(config.WIDTH - 160, None), method="caption")
            .with_duration(duration)
            .with_position("center")
        )
        clip = CompositeVideoClip([clip, text], size=(config.WIDTH, config.HEIGHT))
    except Exception as exc:  # text rendering needs a usable font
        print(f"Skipping text overlay: {exc}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    clip.write_videofile(
        args.out,
        fps=config.FPS,
        codec=config.CODEC,
        audio_codec=config.AUDIO_CODEC,
        ffmpeg_params=["-pix_fmt", config.PIXEL_FORMAT],
    )


if __name__ == "__main__":
    main()
