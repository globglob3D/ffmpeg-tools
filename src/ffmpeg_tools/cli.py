"""
Click CLI entry point for ffmpeg-tools.
"""

import json
import sys
from pathlib import Path

import click

from ffmpeg_tools.ffmpeg import (
    AUDIO_CODEC_MAP,
    CODEC_MAP,
    QUALITY_CRF,
    RESOLUTION_PRESETS,
    build_convert_command,
    get_video_info,
    run_ffmpeg,
)


@click.group()
@click.version_option()
def main() -> None:
    """Personal FFmpeg wrapper for common video conversion tasks."""


@main.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("output_file", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--resolution", "-r",
    default=None,
    metavar="RES",
    help=(
        "Output resolution. "
        f"Presets: {', '.join(RESOLUTION_PRESETS)}. "
        "Or WIDTHxHEIGHT (e.g. 1920x1080)."
    ),
)
@click.option(
    "--framerate", "-f",
    default=None,
    type=float,
    metavar="FPS",
    help="Output framerate (e.g. 24, 30, 60).",
)
@click.option(
    "--quality", "-q",
    default=None,
    metavar="PRESET",
    help=f"Quality preset: {', '.join(QUALITY_CRF)}. Lower quality = smaller file.",
)
@click.option(
    "--crf",
    default=None,
    type=int,
    metavar="VALUE",
    help=(
        "Raw CRF value (0–51 for h264/h265, 0–63 for vp9/av1). "
        "Lower = better quality. Overrides --quality."
    ),
)
@click.option(
    "--video-codec", "-vc",
    default=None,
    metavar="CODEC",
    help=f"Video codec: {', '.join(CODEC_MAP)}.",
)
@click.option(
    "--audio-codec", "-ac",
    default=None,
    metavar="CODEC",
    help=f"Audio codec: {', '.join(AUDIO_CODEC_MAP)}.",
)
@click.option(
    "--audio-bitrate", "-ab",
    default=None,
    metavar="BITRATE",
    help="Audio bitrate (e.g. 128k, 192k, 320k).",
)
@click.option(
    "--no-audio",
    is_flag=True,
    default=False,
    help="Strip the audio track from the output.",
)
@click.option(
    "--overwrite", "-y",
    is_flag=True,
    default=False,
    help="Overwrite output file without prompting.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the ffmpeg command without executing it.",
)
def convert(
    input_file: Path,
    output_file: Path,
    resolution: str | None,
    framerate: float | None,
    quality: str | None,
    crf: int | None,
    video_codec: str | None,
    audio_codec: str | None,
    audio_bitrate: str | None,
    no_audio: bool,
    overwrite: bool,
    dry_run: bool,
) -> None:
    """
    Convert a video file, optionally changing format, resolution, framerate, or quality.

    \b
    Examples:
      fftools convert input.mkv output.mp4
      fftools convert input.mp4 output.mp4 --resolution 1080p
      fftools convert input.mp4 output.mp4 --framerate 30
      fftools convert input.mp4 output.mp4 --quality high
      fftools convert input.mkv output.mp4 --resolution 720p --quality medium --framerate 30
      fftools convert input.mp4 output.mp4 --video-codec h265 --quality high
      fftools convert input.mp4 muted.mp4 --no-audio
      fftools convert input.mkv output.mp4 --dry-run
    """
    if not dry_run and output_file.exists() and not overwrite:
        click.confirm(
            f"Output file '{output_file}' already exists. Overwrite?",
            abort=True,
        )

    try:
        command = build_convert_command(
            input_path=input_file,
            output_path=output_file,
            video_codec=video_codec,
            audio_codec=audio_codec,
            resolution=resolution,
            framerate=framerate,
            quality=quality,
            crf=crf,
            audio_bitrate=audio_bitrate,
            no_audio=no_audio,
            overwrite=overwrite,
        )

        run_ffmpeg(command, dry_run=dry_run)

        if not dry_run:
            click.echo(f"Done: {output_file}")

    except (ValueError, RuntimeError) as error:
        click.echo(f"Error: {error}", err=True)
        sys.exit(1)
    except Exception as error:  # noqa: BLE001
        click.echo(f"Unexpected error: {error}", err=True)
        sys.exit(1)


@main.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--json", "output_json",
    is_flag=True,
    default=False,
    help="Output raw JSON from ffprobe.",
)
def info(input_file: Path, output_json: bool) -> None:
    """Show video file information (codec, resolution, framerate, duration, etc.)."""
    try:
        probe_data = get_video_info(input_file)

        if output_json:
            click.echo(json.dumps(probe_data, indent=2))
            return

        format_data = probe_data.get("format", {})
        streams = probe_data.get("streams", [])

        duration = float(format_data.get("duration", 0))
        file_size = int(format_data.get("size", 0))

        click.echo(f"File:     {input_file}")
        click.echo(f"Duration: {_format_duration(duration)}")
        click.echo(f"Size:     {_format_file_size(file_size)}")
        click.echo(f"Format:   {format_data.get('format_long_name', 'unknown')}")

        for stream in streams:
            codec_type = stream.get("codec_type", "unknown")

            if codec_type == "video":
                _print_video_stream(stream)
            elif codec_type == "audio":
                _print_audio_stream(stream)
            elif codec_type == "subtitle":
                _print_subtitle_stream(stream)

    except (RuntimeError, ValueError) as error:
        click.echo(f"Error: {error}", err=True)
        sys.exit(1)


def _print_video_stream(stream: dict) -> None:
    """
    Print a formatted summary of a video stream.

    :param stream: Stream dictionary from ffprobe output
    """
    width = stream.get("width")
    height = stream.get("height")
    codec_name = stream.get("codec_name", "unknown")
    framerate_value = _eval_fraction(stream.get("avg_frame_rate", "0/0"))
    bit_rate = int(stream.get("bit_rate", 0))

    click.echo(f"\nVideo stream #{stream.get('index')}:")
    click.echo(f"  Codec:      {codec_name}")
    click.echo(f"  Resolution: {width}x{height}")
    click.echo(f"  Framerate:  {framerate_value:.3f} fps")
    if bit_rate:
        click.echo(f"  Bitrate:    {bit_rate // 1000} kbps")


def _print_audio_stream(stream: dict) -> None:
    """
    Print a formatted summary of an audio stream.

    :param stream: Stream dictionary from ffprobe output
    """
    codec_name = stream.get("codec_name", "unknown")
    sample_rate = stream.get("sample_rate", "unknown")
    channels = stream.get("channels", "unknown")
    bit_rate = int(stream.get("bit_rate", 0))
    language = stream.get("tags", {}).get("language", "")

    label = f"Audio stream #{stream.get('index')}"
    if language:
        label += f" [{language}]"

    click.echo(f"\n{label}:")
    click.echo(f"  Codec:       {codec_name}")
    click.echo(f"  Sample rate: {sample_rate} Hz")
    click.echo(f"  Channels:    {channels}")
    if bit_rate:
        click.echo(f"  Bitrate:     {bit_rate // 1000} kbps")


def _print_subtitle_stream(stream: dict) -> None:
    """
    Print a formatted summary of a subtitle stream.

    :param stream: Stream dictionary from ffprobe output
    """
    codec_name = stream.get("codec_name", "unknown")
    language = stream.get("tags", {}).get("language", "")

    label = f"Subtitle stream #{stream.get('index')}"
    if language:
        label += f" [{language}]"

    click.echo(f"\n{label}: {codec_name}")


def _format_duration(total_seconds: float) -> str:
    """
    Format a duration in seconds as HH:MM:SS.

    :param total_seconds: Duration value in seconds
    :returns: Formatted string like '01:23:45'
    """
    total_int = int(total_seconds)
    hours = total_int // 3600
    minutes = (total_int % 3600) // 60
    seconds = total_int % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_file_size(size_bytes: int) -> str:
    """
    Format a byte count as a human-readable size string.

    :param size_bytes: File size in bytes
    :returns: Human-readable string like '1.23 GB'
    """
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"


def _eval_fraction(fraction_string: str) -> float:
    """
    Evaluate a fraction string such as '30000/1001' to a float.

    :param fraction_string: Fraction as 'numerator/denominator' or a plain number string
    :returns: Floating-point result; 0.0 if denominator is zero
    """
    if "/" in fraction_string:
        numerator_str, denominator_str = fraction_string.split("/", 1)
        denominator = int(denominator_str)
        if denominator == 0:
            return 0.0
        return int(numerator_str) / denominator
    return float(fraction_string)
