from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_lofi_video.sh"


def script_text() -> str:
    return SCRIPT.read_text()


def test_uses_suno_duration_plus_rain_outro():
    text = script_text()
    assert "TARGET_SECONDS" not in text
    assert 'RAIN_OUTRO_SECONDS="${RAIN_OUTRO_SECONDS:-5}"' in text
    assert "SUNO_TOTAL_SECONDS" in text
    assert "VIDEO_TOTAL_SECONDS" in text
    assert "suno + outro" in text
    assert '-t "$VIDEO_TOTAL_SECONDS"' in text


def test_builds_one_short_seamless_loop_then_stream_loops_it():
    text = script_text()
    assert 'SEAMLESS_LOOP_FILE="$OUTPUT_DIR/seamless_background_loop.mp4"' in text
    assert "split=2[vbody][vhead]" in text
    assert "asplit=2[abody][ahead]" in text
    assert "atrim=start=${LOOP_CROSSFADE_SECONDS}:end=${BACKGROUND_AUDIO_DURATION_SECONDS}" in text
    assert "atrim=start=0:end=${LOOP_CROSSFADE_SECONDS}" in text
    assert "asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[abody_t]" in text
    assert "asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[ahead_t]" in text
    assert "xfade=transition=fade" in text
    assert "[abody_t][ahead_t]acrossfade=d=${LOOP_CROSSFADE_SECONDS}" in text
    assert '-stream_loop -1 -i "$SEAMLESS_LOOP_FILE"' in text
    assert "split=61" not in text
    assert "asplit=61" not in text


def test_keeps_one_second_crossfade_and_edge_fades():
    text = script_text()
    assert 'LOOP_CROSSFADE_SECONDS="${LOOP_CROSSFADE_SECONDS:-1}"' in text
    assert 'VIDEO_EDGE_FADE_SECONDS="${VIDEO_EDGE_FADE_SECONDS:-1}"' in text
    assert "fade=t=in:st=0:d=${VIDEO_EDGE_FADE_SECONDS}" in text
    assert "fade=t=out:st=${FADE_OUT_START}:d=${VIDEO_EDGE_FADE_SECONDS}" in text


def test_uses_rain_audio_and_suno_mix_when_available():
    text = script_text()
    assert 'BACKGROUND_HAS_AUDIO="yes"' in text
    assert "volume=${BACKGROUND_AUDIO_VOLUME}[background_audio]" in text
    assert "volume=${BGM_VOLUME},apad" in text
    assert "amix=inputs=2:duration=first" in text
    assert "alimiter=limit=${AUDIO_LIMIT}[audio_out]" in text


def test_supports_video_without_rain_audio():
    text = script_text()
    assert 'BACKGROUND_HAS_AUDIO="no"' in text
    assert "-map '[vloop]' -an" in text
    assert "alimiter=limit=${AUDIO_LIMIT}[audio_out]" in text


def test_logs_lightweight_loop_strategy():
    text = script_text()
    assert "seamless_loop_duration_seconds=$LOOP_DURATION_SECONDS" in text
    assert "loop_strategy=single-crossfade-then-stream-loop" in text


def test_validates_seamless_loop_has_video_and_audio_before_final_ffmpeg():
    text = script_text()
    assert "has_video_stream()" in text
    assert "require_video_and_audio_streams()" in text
    assert 'require_video_and_audio_streams "$SEAMLESS_LOOP_FILE" "Seamless background loop"' in text
    assert "Cannot run final FFmpeg because the loop generated from an audio-bearing background has no usable audio stream." in text
    assert "has_positive_audio_duration" in text
    assert "audio stream has no positive duration" in text
    assert 'ffprobe -v error -select_streams v:0' in text
    assert 'ffprobe -v error -select_streams a:0' in text


def test_generates_seamless_loop_with_positive_aac_audio_duration(tmp_path):
    import os
    import shutil
    import subprocess
    from decimal import Decimal

    import pytest

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg and ffprobe are required for real media generation")

    asset_dir = tmp_path / "video_assets"
    track_dir = asset_dir / "tracks"
    output_dir = tmp_path / "dist"
    track_dir.mkdir(parents=True)
    output_dir.mkdir()

    background = asset_dir / "background.mp4"
    track = track_dir / "track01.mp3"

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=64x64:rate=24:duration=3",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "96k", "-shortest", str(background),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=1",
            "-c:a", "libmp3lame", "-q:a", "7", str(track),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    env = os.environ | {
        "ASSET_DIR": str(asset_dir),
        "OUTPUT_DIR": str(output_dir),
        "LOOP_CROSSFADE_SECONDS": "0.5",
        "RAIN_OUTRO_SECONDS": "0",
        "LOOP_PRESET": "ultrafast",
        "LOOP_CRF": "35",
    }
    subprocess.run(["bash", str(SCRIPT)], check=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    loop_file = output_dir / "seamless_background_loop.mp4"
    codec = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", str(loop_file)],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    duration = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(loop_file)],
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    assert codec == "aac"
    assert Decimal(duration) > 0
