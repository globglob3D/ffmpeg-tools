# ffmpeg-tools — Claude.md

## Project overview

Personal CLI tool wrapping FFmpeg for video conversion. Entry point is `fftools` (registered in `pyproject.toml` via `project.scripts`).

## Structure

```
src/ffmpeg_tools/
  __init__.py    version string
  ffmpeg.py      FFmpeg/ffprobe subprocess wrappers, command builders, codec/quality maps
  cli.py         Click commands: `convert` and `info`
```

## Dev setup

```bash
uv venv
.venv\Scripts\activate
uv pip install -e .
fftools --help
```

## Key design decisions

- All FFmpeg logic lives in `ffmpeg.py`; CLI presentation lives in `cli.py`.
- `build_convert_command()` returns a plain `list[str]`; `run_ffmpeg()` executes it. Keeping them separate makes `--dry-run` trivial and the builder unit-testable without subprocess.
- Codec names in `CODEC_MAP` / `AUDIO_CODEC_MAP` are user-facing aliases; ffmpeg library names (e.g. `libx264`) are only used internally.
- `QUALITY_CRF` maps preset names to per-codec CRF values. `--crf` always overrides `--quality`.
- Resolution is passed as a `-vf scale=` filter so aspect ratio is preserved by default.

## Adding a new feature

- New codec: add entry to `CODEC_MAP` or `AUDIO_CODEC_MAP` and the extension-default dicts in `ffmpeg.py`.
- New resolution preset: add entry to `RESOLUTION_PRESETS`.
- New quality preset: add entry to `QUALITY_CRF` with a CRF per codec.
- New CLI option: add `@click.option` to the relevant command in `cli.py`, thread it through to `build_convert_command`.

## Naming conventions

Full descriptive names only — no abbreviations (see global CLAUDE.md).

## Docstrings

Sphinx/rST style on all public functions and modules (see global CLAUDE.md).
