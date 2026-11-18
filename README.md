# Reels

Code that generates short-form vertical videos (Reels / Shorts / TikTok), plus the rendered videos.

## Reels format

| Setting      | Value                     |
|--------------|---------------------------|
| Resolution   | 1080 × 1920 (9:16)        |
| Frame rate   | 30 fps                    |
| Codec        | H.264 (`libx264`), `yuv420p` |
| Audio        | AAC, 44.1 kHz             |
| Length       | up to 90 s                |

These defaults live in `src/config.py`.

## Layout

```
src/            video-generation code
assets/         inputs: images, fonts, music, clips
videos/output/  rendered reels (.mp4)
```

## Quick start

```bash
pip install -r requirements.txt
python src/make_reel.py --text "Hello Reels" --out videos/output/hello.mp4
```

Requires `ffmpeg` on your PATH.

## Large video files

GitHub rejects files over 100 MB. `.gitattributes` routes `*.mp4`, `*.mov`, `*.webm` and
`*.mp3`/`*.wav` through Git LFS. Install it once before committing videos:

```bash
git lfs install
```

## Before → after reels with speed ramps and zooms

```bash
python src/before_after.py projects/surf_02.json
```

Each segment in the JSON can set `speed` (0.5 = slow motion, 2 = fast),
`zoom` (`1.3`, or `[1.0, 1.4]` to zoom in, `[1.4, 1.0]` to zoom out) and `focus`
(where the zoom aims). For a speed ramp, list the same clip several times in a row
with different speeds. See the docstring in `src/before_after.py`.
