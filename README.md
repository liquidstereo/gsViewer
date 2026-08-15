# gsViewer

An interactive, real-time viewer for **3D Gaussian Splatting (3DGS) sequences** --
frame-accurate playback, GPU-accelerated rendering, multiple visualization modes,
and a self-contained plugin system for real-time effects.

---

## Overview

gsViewer preloads a sequence into a 2-tier RAM + GPU cache for disk-free seeking,
renders with `gsplat`, and keeps playback speed fixed and reproducible across
machines.

- **2-tier hybrid cache** -- RAM preload + GPU sliding window (bounds VRAM).
- **10+ visualization modes** -- RGB, Normal, Point, Anisotropy, Opacity,
  Hit Count, Accumulation, Scale, SH, Rotation, Median Depth.
- **Keyframe system** -- camera / object / global keyframes with JSON persistence.
- **Frame export** -- MP4/MOV (ffmpeg) or per-frame PNG/JPG, interactive or batch.
- **Image-sequence inset** and **audio** auto-imported by matching basename.
- **Plugin system** -- self-contained plugins that combine freely and can be
  deleted independently.

| Format | Extension | Notes |
|--------|-----------|-------|
| 3DGS Standard | `.ply` | binary_little_endian, 62-property |
| Point cloud | `.ply` | positions (+ optional colors) only -- GL_POINTS path |
| 3DGS Compressed | `.compressed.ply` | uint8-quantized SH / rotation / opacity |
| SOG | `.sog` | ZIP + WebP tile compression |
| Luma AI Splat | `.splat` | binary blob (DC-only color) |
| Niantic SPZ | `.spz` | v2 (gzip) only; v4 (ZSTD) not supported |

---

## Requirements

- [Python 3.10+](https://www.python.org/downloads/) ·
  [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- **CUDA-capable GPU** (required -- no CPU fallback)
- [ffmpeg](https://www.ffmpeg.org/) on `PATH` (MP4/MOV export only)
- **Linux is strongly recommended.** gsViewer is built and tested on Linux only. Other platforms are untested.

---

## Installation

```bash
git clone https://github.com/liquidstereo/gsViewer.git && cd gsViewer
conda create -n gsViewer python=3.10 && conda activate gsViewer
```

Install the PyTorch build matching your CUDA version from
[pytorch.org](https://pytorch.org/get-started/locally/), then:

```bash
pip install gsplat
pip install -r requirements.txt
```

> **First launch compiles CUDA kernels** (several minutes; may look frozen --
> let it finish). See [Troubleshooting](#troubleshooting).

---

## Quick Start

Place a sequence under `input/data/<name>/`, then:

```bash
python gsviewer.py -i <input>          # load input/data/<input>/
python gsviewer.py -i <input> -r 0-99  # play only frames 0-99
python gsviewer.py -i <input> -t       # start turntable rotation
python gsviewer.py -i <input> -m point # start in a render mode
python gsviewer.py -i <input> -s       # save frames while playing
python gsviewer.py -i <input> -ss      # batch save without a viewer window
```

Left-drag orbits, right-drag pans, scroll dollies. `F1` opens the in-app help.
Exports are written under `output/`.

### Command-line arguments

All flags are optional except `-i`.

**Input**

| Arg | Long form | Description | Default |
|-----|-----------|-------------|---------|
| `-i` | `--input` | **(required)** Sequence dir under `input/data/`, or a direct file / directory path (comma-separated list for multiple inputs) | -- |
| `-r` | `--range` | Playback frame range `START-END` (e.g. `0-499`) | None |
| `-ratio` | `--slicing_ratio` | Keep ratio `0<R<=1` (overrides `SLICING_RATIO`); default `1.0` = no slicing, `R<1.0` enables stride downsampling | None |

**Playback**

| Arg | Long form | Description | Default |
|-----|-----------|-------------|---------|
| `-t` | `--turntable` | Start turntable rotation (toggle: `NumDecimal`) | False |
| `-m` | `--mode` | Startup render mode (overrides `STARTUP_MODE`; e.g. `default` / `point` / `sh`) | default |
| `-no` | `--no_overlay` | Hide all overlays at startup (toggle them back on with `/`) | False |
| `-play` | `--playback_mode` | Multi-input mode `chain`/`loop`/`single`/`shuffle`/`random` (overrides `PLAYBACK_MODE`) | chain |

**Audio**

| Arg | Long form | Description | Default |
|-----|-----------|-------------|---------|
| `-a` | `--audio` | Audio file(s), comma-separated list matching the `-i` inputs 1:1 (auto-detected from `input/audio/<name>` when omitted) | None |

**Plugins**

| Arg | Long form | Description | Default |
|-----|-----------|-------------|---------|
| `-p` | `--plugin` | Comma-separated plugin names (e.g. `crop,noise`) | None |

**Export**

| Arg | Long form | Description | Default |
|-----|-----------|-------------|---------|
| `-s` | `--save` | Auto-save during playback (format per `SAVE_EXT`) | False |
| `-ss` | `--silent_save` | Batch save frames without a viewer window | False |
| `-c` | `--continuous` | Keep saving across loops (use with `-s`) | False |
| `-sq` | `--save_quit` | Show viewer, save the full sequence, then auto-quit | False |
| `-f` | `--format` | Save format `png` / `mp4` (requires `-s`/`-ss`/`-sq`) | None |
| `-q` | `--quality` | Save quality `low`/`medium`/`high`/`raw` (png also `0-100`) | None |

**Debug**

| Arg | Long form | Description | Default |
|-----|-----------|-------------|---------|
| `-v` | `--verbose` | Enable DEBUG-level logging | False |
| -- | `--no-cache` | Disable all caches (disk / RAM / GPU) | False |

---

## Input Directory Structure

```
input/
+-- data/<name>/          <- python gsviewer.py -i <name>
|   +-- frame.0000.ply ...
+-- sequences/<name>/     <- image-sequence inset overlay (optional)
|   +-- frame.0000.png ...
+-- audio/<name>.wav      <- auto-played audio (optional)
```

Audio and the image-sequence inset are auto-imported when a file matches the
input basename; an explicit `-a` always overrides. Set `IGNORE_AUDIO_INPUT` /
`IGNORE_SEQUENCE_INPUT` in `configs/settings.py` to disable name-based
auto-import. A single file may be passed directly (`-i path/to/scene.ply`) and
counts as one frame.

---

## Frame Export

`-s` saves in the format set by `SAVE_EXT` (`configs/settings.py`): `mp4`/`mov`
encodes through an ffmpeg pipe (NVENC when available, else libx264), `png`/`jpg`
writes an image sequence. Saving falls back to PNG if ffmpeg is unavailable.
`-f` overrides the format for one run; `-q low|medium|high|raw` sets quality.

**Output layout (always holds)** -- videos go directly under `output/`, image
sequences go to `output/<input>/`. A numeric suffix (`_01`, `_02`, ...) avoids
overwriting. File stems follow `AVOID_NAME_COLLISION` and, for multiple inputs,
`ABBREVIATE_OUTPUT_FILENAME`.

Saving is **deterministic** -- exactly one rendered frame per step -- so the
export contains every frame regardless of on-screen speed. Overlays are
composited at full resolution and audio is post-muxed to the exact saved frame
count, so the result is complete and A/V-synced. Set `SAVE_WITH_OVERLAY = False`
to skip overlay compositing for a markedly higher save rate.

> **A single-file input needs `-c` to capture more than one frame.** The
> auto-save limit follows the input frame count, and a single file counts as `1`.
> Add `-c / --continuous` to record an animated single input (turntable,
> time-driven plugin, live manipulation). `-c` is mutually exclusive with `-ss`
> and `-sq`. Shuffle/random order is not muxed (silent export).

**Resolution** is width-driven: `WINDOW_WIDTH` + `ASPECT_RATIO`
(`configs/settings_window.py`). `FORCE_RESIZE_WINDOW` + `RESIZE_MAX_HEIGHT` shrink
only the on-screen window; render and save keep the full resolution.

**Live recording (`Ctrl+R`)** records the viewer to `output/liveRec_<stem>.mp4`
in real time, separate from `-s`. Overlays are captured; the recording indicator
and transient messages are not. No audio track. Ignored while `-s` is running.

---

## Playback Modes

With multiple `-i` inputs, `-play / --playback_mode` controls the order; when
omitted the `PLAYBACK_MODE` setting applies.

| Mode | Behavior |
|------|----------|
| `chain` | Play inputs in order, then repeat indefinitely |
| `loop` | Composite all inputs and render together, each looping independently |
| `single` | Play each input once, then freeze on the last frame |
| `shuffle` | Randomized order (fixed for the session), then repeat |
| `random` | Pick a random input on each switch (repeats allowed) |

`-a` is a comma-separated list aligned 1:1 with `-i`. Multi-input `loop` is
silent (no single active track); a single input in `loop` plays its own track.

---

## Plugins

Plugins live in `plugins/<name>/` and attach via `-p` (comma-separated). Each is
self-contained -- deleting its directory disables only that effect.

```bash
python gsviewer.py -i '<input>' -p 'crop,noise'
python gsviewer.py -i '<input>' -p 'crop,crop,noise'   # independent instances
```

Dependencies declared via `REQUIRES_PLUGINS` auto-resolve. Repeating a box
plugin creates independent instances numbered from 1 (`CROP 1`, `CROP 2`);
switch the active box with `Shift+1-9`.

### Registered plugins

| Name | Requires | Depends on | Description |
|------|----------|------------|-------------|
| `crop` | -- | -- | Show only points inside the OBB region, hide the rest (X toggle, T invert) |
| `noise` | -- | -- | Region-confined turbulence + ramp reveal with opacity/size gating (X toggle, T cycle, O/I threshold) |

**Requires** lists external dependencies (CLI flags or Python packages);
**Depends on** lists bundled plugins auto-loaded via `REQUIRES_PLUGINS`.
Per-plugin settings and keys are in each `plugins/<name>/README.txt` and the
in-app plugin help (`F2`).

`audio` and `particle` are **built-in process components**
(`process/component/`), not user plugins -- they cannot be passed to `-p`. The
audio component loads automatically whenever an audio resource exists.

### Plugins on pure point cloud input

A pure point cloud `.ply` (positions/colors only, no Gaussian attributes)
renders through the GL_POINTS path. Only plugins that declare
`POINTCLOUD_SUPPORTED = True` in their `settings.py` take effect there; the
rest are skipped and the viewer reports them once through the message overlay
(`Plugins not supported on point cloud input: ...`), and again whenever their
panel attributes are touched. GL points carry no per-point alpha, so
opacity-driven effects cut at `GLPOINTS_OPACITY_MIN`
(`configs/settings_glpoints.py`) instead of fading out.

### Script Console

Open it from the in-app help (`F2`) to drive any attribute by an expression:

```json
{"DEFAULT_NOISE_THRESHOLD": "audio_band0"}
{"<attribute>": "0.35 + wiggle(2)"}
```

Available variables include per-band audio magnitudes (`audio_band0`, ...) and
three averaged ranges (`audio_low` / `audio_mid` / `audio_high`), plus
`wiggle(x)` (per-frame, seeded/reproducible) and `random(x)` (static per
attribute, bake-stable).

---

## Key Bindings

> **Rebinding.** Bindings live in `configs/keybinding.py` (plugin keys in each
> `plugins/<name>/settings.py`). **Plain keys** (a letter/digit or a Qt key name
> such as `Space`, `Tab`, `F1`, `Slash`) can be changed there directly.
> **Modifier combos and a few special keys** (`[`, `]`, `NumDecimal`) need one
> extra step -- add a matching entry to `_QT_KEY_MOD_MAP` in
> `process/keys/dispatch.py`, or they will **silently fail to fire**.

### Playback & Camera

| Key | Action |
|-----|--------|
| `Space` | Play / Pause |
| `Left` / `Right` | Previous / Next frame |
| `Up` / `Down` | First / Last frame (sequence only) |
| Left-drag | Orbit |
| Right-drag / Wheel-drag | Pan |
| Scroll wheel | Dolly (camera distance) |
| `Ctrl` + Scroll wheel | Zoom (focal length / FOV) |
| `Alt+R` | Reset camera |
| `Tab` | Cycle coordinate transform preset |
| `NumDecimal` | Turntable toggle |
| `S` | Solo selected object / region (gate editing, hide the rest) |
| `Alt+Shift+R` | Reset selected object transform |
| `Ctrl+Home` | Reset all + delete saved session JSON (warn dialog) |
| `Escape` | Quit (confirm dialog) |

### Render modes

| Key | Action |
|-----|--------|
| `Q` | Default RGB |
| `1`-`0` | Normal / Point / Anisotropy / Opacity / Hit Count / Accumulation / Scale / SH / Rotation / Median Depth |
| `]` / `[` | Splat size up / down |
| `\` | Reset splat size |
| `Ctrl+]` / `Ctrl+[` | Slice ratio up / down (runtime stride downsample; VRAM/FPS) |
| `Ctrl+\` | Reset slice ratio to launch value |

### Overlays & scene

| Key | Action |
|-----|--------|
| `F1` / `F2` | Help overlay / Plugin help overlay |
| `/` | Toggle all overlays |
| `U` | Compact overlays for higher FPS |
| `,` | Toggle bottom-right sequence inset |
| `;` | Toggle attribute panel |
| `'` | Bbox + Grid toggle |
| `C` | Colormap toggle |
| `B` / `Shift+B` | Depth occlusion / Corner-bracket display toggle |
| `Ctrl+B` | Cycle color theme (Bright <-> Dark, session only) |
| `F` | Fog toggle |
| `.` | Log overlay toggle |
| `` ` `` | Save screenshot |
| `Ctrl+R` | Live record current viewer to mp4 (toggle; silent, separate from `-s` batch save) |

`/` toggles every overlay at once (help, attribute panel, bbox/grid, sequence
inset, and the rest). Launch with `-no / --no_overlay` to start with all overlays
hidden for a clean first frame -- for example when saving or screenshotting a bare
render -- then press `/` to bring them back on demand.

### Keyframes

| Key | Action |
|-----|--------|
| `A` / `D` | Add / Remove last global keyframe (objects + regions) |
| `P` | Toggle global keyframe markers |
| `Ctrl+Delete` | Clear all global keyframes |
| `Ctrl+PageUp` / `Ctrl+PageDown` | Prev / Next global keyframe |
| `Alt+A` / `Alt+D` / `Alt+Delete` | Add / Remove / Clear camera keyframes |
| `Alt+P` / `Alt+PageUp` / `Alt+PageDown` | Camera keyframe overlay / navigate |
| `Alt+Shift+A` / `Alt+Shift+D` / `Alt+Shift+Delete` | Add / Remove / Clear object keyframes |
| `Alt+Shift+P` / `Alt+Shift+PageUp` / `Alt+Shift+PageDown` | Object keyframe markers / navigate |

### Orthographic views (toggle)

| Key | Action |
|-----|--------|
| `F5`-`F10` | Front / Back / Left / Right / Top / Bottom |

Plugin keys are shown in the in-app plugin help (`F2`).

---

## Format Converter (`utils/convert3DGS.py`)

Converts between 3DGS formats through a unified in-memory buffer; single-file and
batch-directory conversion are both supported.

| Input | Output options |
|-------|----------------|
| `.ply` | `.compressed.ply`, `.splat` |
| `.compressed.ply` | `.ply`, `.splat` |
| `.splat` | `.ply`, `.compressed.ply` |

```bash
# Single file
python utils/convert3DGS.py -i input.ply -c splat
python utils/convert3DGS.py -i input.ply -o scene.compressed.ply

# Batch directory -> <dir>_<codec>/
python utils/convert3DGS.py -i ./input/data/<input> -c splat
```

| Arg | Long form | Description |
|-----|-----------|-------------|
| `-i` | `--input` | Input file or directory |
| `-o` | `--output` | Output file or directory (auto-named if omitted) |
| `-c` | `--codec` | Target format: `ply` / `cply` (alias of `.compressed.ply`) / `splat` |

> Converting to `.splat` keeps DC color only (higher-order SH discarded), so it
> is much smaller and **loads far faster** -- on a 1341-frame capture, RAM
> preload dropped from ~105 s (`.ply`) to ~21 s (`.splat`), roughly **5x faster
> startup**. Convert once and play the `.splat` when view-dependent shading is
> not needed.

---

## Caching

Decoded frames are cached as `.npz` under `input/cache/` for `.ply` / `.sog` /
`.compressed.ply`; compact `.splat` / `.spz` are read directly. A cache hit is
validated by file **size + mtime** (O(1)), falling back to MD5 only when metadata
changes.

Spherical-harmonics color is ~80% of the per-point data, so `CACHING_METHOD`
(`configs/settings.py`) dominates cache size and load speed:

| `CACHING_METHOD` | SH storage | Cache size / load | Quality |
|---|---|---|---|
| `fp32` | full SH, full precision | largest, slowest | lossless |
| `fp16` | full SH, half precision | ~1/2, ~1.7x faster | near-lossless |
| `dc` | DC only | smallest, fastest | flat color (no view-dependent SH) |

Changing `CACHING_METHOD` auto-rebuilds caches on the next load.

---

## Performance & Tuning

Frame rate is **hardware-dependent**; **playback speed is not**. The render loop
runs uncapped (that is the on-screen FPS), while the sequence advances on a fixed
wall-clock at `PLAYBACK_FPS` (`configs/settings.py`), identical on every machine.
Heavier data lowers the *frame rate* and lengthens load/seek times -- it never
changes sequence *duration*, A/V sync, or exported frame count.

**If the frame rate is low, in this order:**

1. `-ratio 0.5` / `--slicing_ratio` -- stride-downsample points per frame
   (largest single win; `Ctrl+]` / `Ctrl+[` adjust it live, `Ctrl+\` resets).
2. `-r START-END` -- shorten the played range.
3. `-p` only the plugins you actually use.
4. Reduce `WINDOW_WIDTH`; keep `SSAA_SCALE` at 1 (super-sampling costs ~N^2).
5. Convert to `.splat`, or set `CACHING_METHOD = 'dc'` (both drop higher-order SH).

**What costs the most**

| Factor | Effect |
|---|---|
| Gaussians per frame | Dominant -- H2D upload + rasterization both scale with it |
| Render resolution / `SSAA_SCALE` | Pixel work; SSAA is roughly N-squared |
| Audio playback | Lowers FPS on heavy sequences (disable auto-import to avoid) |
| Saving (`-s`) with overlays | Per-frame full-resolution compositing on the GUI thread |
| bbox / grid overlays | Enables depth occlusion; measurable FPS drop |

**VRAM / RAM** -- the GPU sliding window bounds VRAM; RAM preload assumes the
sequence fits in system memory. Keep `OPACITY_PRUNE_ENABLED` on to drop
near-invisible Gaussians at load.

**Stride downsampling** (`-ratio` / `--slicing_ratio`) keeps a ratio `0<R<=1` of
points per frame and overrides the `SLICING_RATIO` setting. `R = 1.0` disables
it. Changing it at runtime rebuilds the working set behind a loading overlay;
playback and audio pause until the GPU window is warm, then resume in sync. Use
it for fast previewing, then restore full fidelity for export.

---

## Troubleshooting

### Hangs at "COMPILING CUDA SHADERS..." on first launch

gsplat compiles CUDA kernels just-in-time on first launch (or after upgrading
PyTorch / gsplat / CUDA). This takes several minutes and looks frozen --
**do not interrupt it**. An interrupted build never links, so every later launch
restarts the compile. Recover by building once without the GUI:

```bash
rm -f ~/.cache/torch_extensions/py310_cu118/gsplat_cuda/lock
python -c "from gsplat.cuda._backend import _C; print('EXT OK', _C)"
python gsviewer.py -i <input>
```

If it still fails, wipe the build cache and rebuild:

```bash
rm -rf ~/.cache/torch_extensions/py310_cu118/gsplat_cuda
python -c "from gsplat.cuda._backend import _C; print('EXT OK', _C)"
```

> The path suffix (`py310_cu118`) reflects your Python and CUDA versions.

### Edited input not reflected (stale cache)

`.ply` / `.compressed.ply` / `.sog` are MD5-verified, so edits invalidate the
cache automatically. `.splat` / `.spz` inputs and the image-sequence inset are
keyed by **filename only** and can serve stale content after an in-place edit.

```bash
python gsviewer.py -i <input> --no-cache   # bypass caches for one run
rm -rf input/cache/<input>                 # or clear only the cache entry
```

**Never** delete the original input under `input/data/`.

---

## Roadmap

- **Timeline editor** for authoring keyframe animations.
- **`.spz` v4 (ZSTD)** decode support.
- **Bounding box / grid performance** -- optimize the FPS drop when enabled.
- **More plugins & effects**, and a **plugin authoring guide**.

---

## License

This project is licensed under [CC BY-NC 4.0](http://creativecommons.org/licenses/by-nc/4.0/).
