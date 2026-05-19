# ffmpeg-tools

Personal CLI wrapper around FFmpeg for common video conversion tasks: format conversion, resolution changes, framerate changes, and quality/size adjustments.

## Requirements

- Python 3.11+
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on `PATH`

### Installing FFmpeg on Windows

Download a build from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) (e.g. the [BtbN builds](https://github.com/BtbN/FFmpeg-Builds/releases)) and add the `bin/` folder to your system `PATH`.

## Installation

```bash
# Create and activate the virtual environment
uv venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# Install the package in editable mode
uv pip install -e .
```

The `fftools` command is now available in the activated environment.

## Usage

### Convert format

```bash
fftools convert input.mkv output.mp4
```

### Change resolution

```bash
# Named preset (480p, 720p, 1080p, 1440p, 4k / 2160p)
fftools convert input.mp4 output.mp4 --resolution 720p

# Explicit dimensions
fftools convert input.mp4 output.mp4 --resolution 1280x720
```

### Change framerate

```bash
fftools convert input.mp4 output.mp4 --framerate 30
```

### Change quality / reduce file size

Quality presets control the CRF value. Lower quality = smaller file.

| Preset    | Description                                |
|-----------|--------------------------------------------|
| `low`     | Heavy compression, smallest file           |
| `medium`  | Default FFmpeg quality (good balance)      |
| `high`    | Low compression, large file, great quality |
| `lossless`| No quality loss (very large file)          |

```bash
fftools convert input.mp4 output.mp4 --quality low
fftools convert input.mp4 output.mp4 --quality high

# Raw CRF (0–51 for h264/h265, 0–63 for vp9/av1; lower = better)
fftools convert input.mp4 output.mp4 --crf 28
```

### Change video codec

```bash
# h264 (default), h265, vp9, av1, copy
fftools convert input.mkv output.mp4 --video-codec h265
```

### Audio options

```bash
# Change audio codec (aac, mp3, opus, vorbis, copy)
fftools convert input.mkv output.mp4 --audio-codec opus --audio-bitrate 192k

# Strip audio entirely
fftools convert input.mp4 muted.mp4 --no-audio
```

### Combine options

```bash
fftools convert input.mkv output.mp4 --resolution 1080p --quality medium --framerate 30
```

### Preview the command without running it

```bash
fftools convert input.mkv output.mp4 --resolution 720p --quality low --dry-run
```

### Show file info

```bash
fftools info input.mp4

# Raw JSON output from ffprobe
fftools info input.mp4 --json
```

## All options

```
fftools convert INPUT_FILE OUTPUT_FILE [OPTIONS]

  -r, --resolution RES      480p / 720p / 1080p / 1440p / 4k or WIDTHxHEIGHT
  -f, --framerate FPS       Target frames per second
  -q, --quality PRESET      low / medium / high / lossless
      --crf VALUE           Raw CRF value (overrides --quality)
  -vc, --video-codec CODEC  h264 / h265 / hevc / vp9 / av1 / copy
  -ac, --audio-codec CODEC  aac / mp3 / opus / vorbis / copy
  -ab, --audio-bitrate      e.g. 128k, 192k, 320k
      --no-audio            Strip audio track
  -y,  --overwrite          Overwrite output without prompting
       --dry-run            Print command, do not run

fftools info INPUT_FILE [OPTIONS]
      --json                Raw ffprobe JSON output
```
