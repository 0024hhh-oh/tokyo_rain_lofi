import os
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_lofi_video.sh"


def script_text() -> str:
    return SCRIPT.read_text(encoding="utf-8")


def test_uses_suno_duration_plus_rain_outro():
    text = script_text()
    assert "TARGET_SECONDS" not in text
    assert 'RAIN_OUTRO_SECONDS="${RAIN_OUTRO_SECONDS:-5}"' in text
    assert "SUNO_TOTAL_SECONDS" in text
    assert "VIDEO_TOTAL_SECONDS" in text
    assert "suno + outro" in text
    assert '-t "$VIDEO_TOTAL_SECONDS"' in text


def test_separates_silent_visual_loop_and_shared_rain_audio():
    text = script_text()
    assert 'RAIN_AUDIO_SOURCE="${RAIN_AUDIO_SOURCE:-$ASSET_DIR/rain_audio_source.mp4}"' in text
    assert 'background_audio_ignored=yes' in text
    assert '"${BACKGROUND_INPUT_ARGS[@]}"' in text
    assert '-stream_loop -1 -i "$RAIN_AUDIO_SOURCE"' in text
    assert "[0:v]" in text
    assert "[1:a]" in text
    assert "[2:a]" in text


def test_removes_old_crossfade_and_procedural_rain_paths():
    text = script_text()
    assert "crossfaded_background_audio" not in text
    assert "acrossfade" not in text
    assert "CROSSFADED_BACKGROUND_AUDIO_CODEC" not in text
    assert "ENABLE_RAIN_OVERLAY" not in text
    assert "blend=all_mode=screen" not in text


def test_loops_or_trims_rain_to_the_full_video_length_without_crossfade():
    text = script_text()
    assert "rain_audio_loop_strategy=stream-loop-without-crossfade" in text
    assert "atrim=0:${VIDEO_TOTAL_SECONDS}" in text
    assert "amix=inputs=2:duration=first" in text
    assert "alimiter=limit=${AUDIO_LIMIT}[audio_out]" in text


def test_generates_video_with_silent_background_input_and_separate_rain_source(
    tmp_path,
):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are required for real media generation")

    asset_dir = tmp_path / "video_assets"
    track_dir = asset_dir / "tracks"
    output_dir = tmp_path / "dist"
    track_dir.mkdir(parents=True)
    output_dir.mkdir()

    background = asset_dir / "background.mp4"
    rain_source = asset_dir / "rain_audio_source.mp4"
    track = track_dir / "track01.mp3"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:rate=24:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:sample_rate=48000:duration=2",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(background),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=black:size=16x16:rate=5:duration=0.4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=0.4",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(rain_source),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=48000:duration=1",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "7",
            str(track),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    env = os.environ | {
        "ASSET_DIR": str(asset_dir),
        "OUTPUT_DIR": str(output_dir),
        "OUTPUT_FILE": "separate-rain-test.mp4",
        "RAIN_OUTRO_SECONDS": "0",
        "VIDEO_EDGE_FADE_SECONDS": "0",
        "VIDEO_PRESET": "ultrafast",
        "VIDEO_CRF": "35",
        "VIDEO_WIDTH": "64",
        "VIDEO_HEIGHT": "64",
        "VIDEO_FPS": "24",
    }
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        check=False,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    output = output_dir / "separate-rain-test.mp4"
    assert output.is_file()
    assert output.stat().st_size > 0
    assert not (output_dir / "crossfaded_background_audio.m4a").exists()

    streams = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(output),
        ],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    assert "video" in streams
    assert "audio" in streams

    output_duration = Decimal(
        subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(output),
            ],
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
    )
    assert output_duration > Decimal("0.9")
