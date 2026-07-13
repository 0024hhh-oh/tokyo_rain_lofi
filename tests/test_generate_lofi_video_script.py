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


def test_separates_rain_audio_and_crossfades_audio_only_loop():
    text = script_text()
    assert 'TRIMMED_BACKGROUND_LOOP_FILE="$OUTPUT_DIR/trimmed_background_loop.mp4"' in text
    assert 'BACKGROUND_AUDIO_LOOP_FILE="$OUTPUT_DIR/crossfaded_background_audio.m4a"' in text
    assert "split=2[vbody][vhead]" not in text
    assert "asplit=3[amid][atail][ahead]" in text
    assert '-ss "$BACKGROUND_LOOP_TRIM_START_SECONDS"' in text
    assert '-t "$TRIMMED_BACKGROUND_DURATION_SECONDS"' in text
    assert "atrim=start=${LOOP_CROSSFADE_SECONDS}:end=${BACKGROUND_AUDIO_MID_END_SECONDS}" in text
    assert "atrim=start=${BACKGROUND_AUDIO_MID_END_SECONDS}:end=${BACKGROUND_AUDIO_DURATION_SECONDS}" in text
    assert "atrim=start=0:end=${LOOP_CROSSFADE_SECONDS}" in text
    assert "adelay=${BACKGROUND_AUDIO_HEAD_DELAY_SAMPLES}S:all=1" in text
    assert "asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[amid_t]" in text
    assert "asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[atail_t]" in text
    assert "asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[ahead_t]" in text
    assert "xfade=transition=fade" not in text
    assert "[atail_t][ahead_t]acrossfade=d=${LOOP_CROSSFADE_SECONDS}:c1=tri:c2=tri[aseam]" in text
    assert "[amid_t][aseam]concat=n=2:v=0:a=1[out]" in text
    assert "-map '[out]' -vn" in text
    assert '-stream_loop -1 -i "$TRIMMED_BACKGROUND_LOOP_FILE"' in text
    assert '-stream_loop -1 -i "$SOURCE_BACKGROUND_FILE"' not in text
    assert '-stream_loop -1 -i "$BACKGROUND_AUDIO_LOOP_FILE"' in text
    assert "split=61" not in text
    assert "asplit=61" not in text


def test_keeps_one_second_crossfade_and_edge_fades():
    text = script_text()
    assert 'LOOP_CROSSFADE_SECONDS="${LOOP_CROSSFADE_SECONDS:-1}"' in text
    assert 'VIDEO_EDGE_FADE_SECONDS="${VIDEO_EDGE_FADE_SECONDS:-1}"' in text
    assert "fade=t=in:st=0:d=${VIDEO_EDGE_FADE_SECONDS}" in text
    assert "fade=t=out:st=${FADE_OUT_START}:d=${VIDEO_EDGE_FADE_SECONDS}" in text


def test_generates_visible_procedural_rain_overlay_by_default():
    text = script_text()
    assert 'ENABLE_RAIN_OVERLAY="${ENABLE_RAIN_OVERLAY:-1}"' in text
    assert 'RAIN_OVERLAY_OPACITY="${RAIN_OVERLAY_OPACITY:-0.55}"' in text
    assert 'RAIN_DENSITY_THRESHOLD="${RAIN_DENSITY_THRESHOLD:-0.996}"' in text
    assert "[0:v]split=2[video_source][rain_seed]" in text
    assert "gblur=sigma=0.3:sigmaV=6" in text
    assert "scroll=horizontal=-0.003:vertical=0.04" in text
    assert "blend=all_mode=screen:all_opacity=${RAIN_OVERLAY_OPACITY}" in text
    assert "format=gbrp[video_base_rgb]" in text
    assert "format=gbrp[rain_layer_rgb]" in text
    assert "[video_base_rgb][rain_layer_rgb]blend=" in text
    assert "[video_base][rain_layer]blend=" not in text
    assert 'RAIN_OVERLAY_STATUS="generated-visible-rain"' in text


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
    assert "-map '[vloop]' -an" not in text
    assert "alimiter=limit=${AUDIO_LIMIT}[audio_out]" in text


def test_logs_audio_only_crossfade_loop_strategy():
    text = script_text()
    assert "trimmed_background_duration_seconds=$TRIMMED_BACKGROUND_DURATION_SECONDS" in text
    assert "seamless_loop_duration_seconds=$LOOP_DURATION_SECONDS" in text
    assert "loop_strategy=trimmed-video-loop-with-audio-only-crossfade" in text


def test_validates_source_video_and_background_audio_duration():
    text = script_text()
    assert "has_video_stream()" in text
    assert "require_video_and_audio_streams()" in text
    assert 'require_video_and_audio_streams "$SEAMLESS_LOOP_FILE" "Seamless background loop"' not in text
    assert "Background source is missing a video stream" in text
    assert "Trimmed background loop is missing a video stream" in text
    assert "has_positive_audio_duration" in text
    assert "validate_crossfaded_audio_loop" in text
    assert "audio stream has no positive duration" in text
    assert 'ffprobe -v error -select_streams v:0' in text
    assert 'ffprobe -v error -select_streams a:0' in text


def test_stops_instead_of_falling_back_when_crossfade_file_is_unusable():
    text = script_text()
    assert '[[ ! -s "$file" ]]' in text
    assert 'validate_crossfaded_audio_loop "$BACKGROUND_AUDIO_LOOP_FILE" "$BACKGROUND_AUDIO_LOOP_EXPECTED_SECONDS"' in text
    assert 'rm -f "$BACKGROUND_AUDIO_LOOP_FILE"' in text
    assert "fallback-trimmed-background-loop-audio" not in text
    assert "stopping before video generation" in text
    assert '-stream_loop -1 -i "$BACKGROUND_AUDIO_LOOP_FILE"' in text
    assert "BACKGROUND_AUDIO_INPUT_FILE" not in text


def test_generates_crossfaded_audio_loop_with_positive_aac_audio_duration(tmp_path):
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
        "BACKGROUND_LOOP_TRIM_START_SECONDS": "0.25",
        "BACKGROUND_LOOP_TRIM_END_SECONDS": "0.25",
        "ENABLE_RAIN_OVERLAY": "0",
    }
    subprocess.run(["bash", str(SCRIPT)], check=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    trimmed_loop_file = output_dir / "trimmed_background_loop.mp4"
    assert trimmed_loop_file.exists()

    loop_file = output_dir / "crossfaded_background_audio.m4a"
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
    assert abs(Decimal(duration) - Decimal("2.0")) <= Decimal("0.1")


def test_stops_when_crossfade_generation_fails(tmp_path):
    import os
    import shutil
    import subprocess

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
        "BACKGROUND_LOOP_TRIM_START_SECONDS": "0.25",
        "BACKGROUND_LOOP_TRIM_END_SECONDS": "0.25",
        "CROSSFADED_BACKGROUND_AUDIO_CODEC": "definitely_not_a_codec",
        "ENABLE_RAIN_OVERLAY": "0",
    }
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        check=False,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode != 0
    assert "Crossfaded background audio loop generation failed; stopping before video generation" in result.stderr
    assert not (output_dir / "crossfaded_background_audio.m4a").exists()
    assert not (output_dir / "Tokyo_Memory_Archive_001.mp4").exists()
