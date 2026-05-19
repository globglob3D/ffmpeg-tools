"""
FFmpeg subprocess wrapper — command building and execution.
"""

import json
import shutil
import subprocess
from pathlib import Path


CODEC_MAP: dict[str, str] = {
    "h264": "libx264",
    "h265": "libx265",
    "hevc": "libx265",
    "vp9": "libvpx-vp9",
    "av1": "libsvtav1",
    "copy": "copy",
}

AUDIO_CODEC_MAP: dict[str, str] = {
    "aac": "aac",
    "mp3": "libmp3lame",
    "opus": "libopus",
    "vorbis": "libvorbis",
    "copy": "copy",
}

RESOLUTION_PRESETS: dict[str, str] = {
    "480p": "854:480",
    "720p": "1280:720",
    "1080p": "1920:1080",
    "1440p": "2560:1440",
    "4k": "3840:2160",
    "2160p": "3840:2160",
}

# CRF values per codec; lower value = better quality, larger file
QUALITY_CRF: dict[str, dict[str, int]] = {
    "low": {"libx264": 35, "libx265": 35, "libvpx-vp9": 45, "libsvtav1": 50},
    "medium": {"libx264": 23, "libx265": 28, "libvpx-vp9": 33, "libsvtav1": 35},
    "high": {"libx264": 18, "libx265": 22, "libvpx-vp9": 24, "libsvtav1": 25},
    "lossless": {"libx264": 0, "libx265": 0, "libvpx-vp9": 0, "libsvtav1": 0},
}

_EXTENSION_VIDEO_DEFAULTS: dict[str, str] = {
    ".mp4": "libx264",
    ".mkv": "libx264",
    ".webm": "libvpx-vp9",
    ".avi": "libx264",
    ".mov": "libx264",
}

_EXTENSION_AUDIO_DEFAULTS: dict[str, str] = {
    ".mp4": "aac",
    ".mkv": "aac",
    ".webm": "libopus",
    ".avi": "aac",
    ".mov": "aac",
}


def _require_binary(binary_name: str) -> str:
    """
    Locate a binary on PATH or raise a clear error.

    :param binary_name: Name of the binary to find (e.g. 'ffmpeg')
    :returns: Absolute path to the binary
    :raises RuntimeError: If the binary is not found
    """
    binary_path = shutil.which(binary_name)
    if not binary_path:
        raise RuntimeError(
            f"'{binary_name}' not found in PATH. "
            "Install FFmpeg from https://ffmpeg.org/download.html and ensure it is on your PATH."
        )
    return binary_path


def parse_resolution(resolution: str) -> str:
    """
    Parse a resolution string into an ffmpeg scale filter value.

    :param resolution: Preset name (e.g. '1080p') or WIDTHxHEIGHT (e.g. '1920x1080')
    :returns: Scale filter value in 'WIDTH:HEIGHT' format (e.g. '1920:1080')
    :raises ValueError: If the resolution string is not a recognised preset or valid WIDTHxHEIGHT
    """
    normalised = resolution.lower()
    if normalised in RESOLUTION_PRESETS:
        return RESOLUTION_PRESETS[normalised]

    if "x" in normalised:
        parts = normalised.split("x", 1)
        if len(parts) == 2 and all(part.isdigit() for part in parts):
            return f"{parts[0]}:{parts[1]}"

    valid_presets = ", ".join(RESOLUTION_PRESETS)
    raise ValueError(
        f"Invalid resolution '{resolution}'. "
        f"Use a preset ({valid_presets}) or WIDTHxHEIGHT format (e.g. 1920x1080)."
    )


def resolve_video_codec(codec_name: str | None, output_path: Path) -> str:
    """
    Resolve a user-provided codec name to its ffmpeg library identifier.

    Falls back to an extension-based default when no codec is specified.

    :param codec_name: User-provided codec name, or None for auto-detection
    :param output_path: Output file path used for extension-based inference
    :returns: ffmpeg codec identifier (e.g. 'libx264')
    :raises ValueError: If codec_name is provided but not recognised
    """
    if codec_name:
        resolved = CODEC_MAP.get(codec_name.lower())
        if not resolved:
            raise ValueError(
                f"Unknown video codec '{codec_name}'. "
                f"Valid options: {', '.join(CODEC_MAP)}."
            )
        return resolved

    return _EXTENSION_VIDEO_DEFAULTS.get(output_path.suffix.lower(), "libx264")


def resolve_audio_codec(codec_name: str | None, output_path: Path) -> str:
    """
    Resolve a user-provided audio codec name to its ffmpeg library identifier.

    Falls back to an extension-based default when no codec is specified.

    :param codec_name: User-provided codec name, or None for auto-detection
    :param output_path: Output file path used for extension-based inference
    :returns: ffmpeg audio codec identifier (e.g. 'aac')
    :raises ValueError: If codec_name is provided but not recognised
    """
    if codec_name:
        resolved = AUDIO_CODEC_MAP.get(codec_name.lower())
        if not resolved:
            raise ValueError(
                f"Unknown audio codec '{codec_name}'. "
                f"Valid options: {', '.join(AUDIO_CODEC_MAP)}."
            )
        return resolved

    return _EXTENSION_AUDIO_DEFAULTS.get(output_path.suffix.lower(), "aac")


def build_convert_command(
    input_path: Path,
    output_path: Path,
    video_codec: str | None = None,
    audio_codec: str | None = None,
    resolution: str | None = None,
    framerate: float | None = None,
    quality: str | None = None,
    crf: int | None = None,
    audio_bitrate: str | None = None,
    no_audio: bool = False,
    overwrite: bool = False,
) -> list[str]:
    """
    Build an ffmpeg command list for video conversion.

    :param input_path: Input video file path
    :param output_path: Desired output file path
    :param video_codec: Video codec name (h264, h265, vp9, av1, copy)
    :param audio_codec: Audio codec name (aac, mp3, opus, vorbis, copy)
    :param resolution: Target resolution as preset or WIDTHxHEIGHT string
    :param framerate: Target frames per second
    :param quality: Quality preset name (low, medium, high, lossless)
    :param crf: Raw CRF value; takes precedence over quality preset
    :param audio_bitrate: Audio bitrate string (e.g. '192k')
    :param no_audio: Strip the audio track from the output
    :param overwrite: Pass -y to ffmpeg to overwrite the output without prompting
    :returns: Argument list suitable for subprocess
    :raises ValueError: If any option value is invalid
    :raises RuntimeError: If ffmpeg is not found on PATH
    """
    ffmpeg_binary = _require_binary("ffmpeg")
    resolved_video_codec = resolve_video_codec(video_codec, output_path)

    command: list[str] = [ffmpeg_binary]
    if overwrite:
        command.append("-y")
    command += ["-i", str(input_path)]

    command += ["-c:v", resolved_video_codec]

    if resolved_video_codec != "copy":
        effective_crf: int | None = None
        if crf is not None:
            effective_crf = crf
        elif quality:
            codec_crf_map = QUALITY_CRF.get(quality.lower())
            if not codec_crf_map:
                raise ValueError(
                    f"Unknown quality preset '{quality}'. "
                    f"Valid options: {', '.join(QUALITY_CRF)}."
                )
            effective_crf = codec_crf_map.get(resolved_video_codec, 23)

        if effective_crf is not None:
            command += ["-crf", str(effective_crf)]

        if resolution:
            scale_value = parse_resolution(resolution)
            command += ["-vf", f"scale={scale_value}"]

        if framerate:
            command += ["-r", str(framerate)]

    if no_audio:
        command.append("-an")
    else:
        resolved_audio_codec = resolve_audio_codec(audio_codec, output_path)
        command += ["-c:a", resolved_audio_codec]
        if audio_bitrate and resolved_audio_codec != "copy":
            command += ["-b:a", audio_bitrate]

    command.append(str(output_path))
    return command


def run_ffmpeg(command: list[str], dry_run: bool = False) -> None:
    """
    Execute an ffmpeg command, streaming its output to the terminal.

    :param command: Argument list as returned by build_convert_command
    :param dry_run: Print the command instead of running it
    :raises subprocess.CalledProcessError: If ffmpeg exits with a non-zero status
    """
    if dry_run:
        print("Would run:", " ".join(command))
        return

    result = subprocess.run(command)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, command)


def get_video_info(input_path: Path) -> dict:
    """
    Retrieve video file metadata via ffprobe.

    :param input_path: Path to the video file
    :returns: Dictionary with 'streams' and 'format' keys as returned by ffprobe
    :raises RuntimeError: If ffprobe is not found or fails to read the file
    """
    ffprobe_binary = _require_binary("ffprobe")

    command = [
        ffprobe_binary,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(input_path),
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    return json.loads(result.stdout)
