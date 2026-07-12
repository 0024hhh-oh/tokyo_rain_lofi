from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_lofi_video.sh"


def script_text() -> str:
    return SCRIPT.read_text()


def test_script_uses_suno_plus_rain_outro_duration_instead_of_fixed_target_seconds():
    text = script_text()

    assert "TARGET_SECONDS" not in text
    assert "SUNO_TOTAL_SECONDS" in text
    assert "VIDEO_TOTAL_SECONDS" in text
    assert "RAIN_OUTRO_SECONDS=\"${RAIN_OUTRO_SECONDS:-5}\"" in text
    assert "ffprobe" in text
    assert "total += duration" in text
    assert "suno_total + rain_outro" in text
    assert "-t \"$VIDEO_TOTAL_SECONDS\"" in text


def test_script_loops_background_but_not_suno_concat_input():
    text = script_text()

    assert '-stream_loop -1 -i "$BACKGROUND_FILE"' in text
    assert '-stream_loop -1 -f concat' not in text
    assert '-f concat -safe 0 -i "$CONCAT_FILE"' in text
    assert "[2:a]atrim=0:${SUNO_TOTAL_SECONDS}" in text
    assert "volume=${BGM_VOLUME},apad,atrim=0:${VIDEO_TOTAL_SECONDS}[suno_bgm]" in text
    assert "[1:a]aresample=48000,aloop=loop=-1:size=${BACKGROUND_AUDIO_LOOP_SAMPLES},atrim=0:${VIDEO_TOTAL_SECONDS}" in text
    assert "BACKGROUND_AUDIO_LOOP_SAMPLES" in text
    assert "amix=inputs=2:duration=first" in text
    assert "amix=inputs=2:duration=shortest" not in text


def test_script_keeps_background_rain_audio_through_outro_without_fade():
    text = script_text()

    assert 'BACKGROUND_AUDIO_VOLUME="${BACKGROUND_AUDIO_VOLUME:-1.0}"' in text
    assert "[1:a]aresample=48000,aloop=loop=-1:size=${BACKGROUND_AUDIO_LOOP_SAMPLES},atrim=0:${VIDEO_TOTAL_SECONDS},asetpts=N/SR/TB,volume=${BACKGROUND_AUDIO_VOLUME}[background_audio]" in text
    assert "math.ceil(float(duration) * 48000)" in text
    assert "dropout_transition=0" in text
    assert "afade" not in text
    assert "fade=t=out" not in text


def test_script_generates_background_seamless_mp4_from_drive_background():
    text = script_text()

    assert "LOOP_CROSSFADE_SECONDS=\"${LOOP_CROSSFADE_SECONDS:-1.5}\"" in text
    assert "BACKGROUND_FILE=\"$ASSET_DIR/background_seamless.mp4\"" in text
    assert "-name 'background.mp4'" in text
    assert "generate_seamless_background \"$SOURCE_BACKGROUND_FILE\" \"$BACKGROUND_FILE\"" in text
    assert "Seamless loop generation completed" in text


def test_script_honors_loop_crossfade_env_and_rejects_too_short_source():
    text = script_text()

    assert "LOOP_CROSSFADE_SECONDS=\"${LOOP_CROSSFADE_SECONDS:-1.5}\"" in text
    assert "crossfade_seconds=\"$3\"" in text
    assert "duration <= crossfade * 2" in text
    assert "Background video is too short for seamless loop generation" in text
    assert "required duration >" in text


def test_script_generates_seamless_loop_as_video_only_without_audio_crossfade():
    text = script_text()

    assert "has_audio_stream" in text
    assert "xfade=transition=fade:duration=${crossfade_seconds}:offset=${offset}" in text
    assert "acrossfade" not in text
    assert "-map \"[vout]\"" in text
    assert "-an" in text
    assert "-map \"[aout]\"" not in text


def test_script_supports_silent_background_during_seamless_generation():
    text = script_text()

    assert "Background audio stream: $has_audio" in text
    assert "-map \"[vout]\"" in text
    assert "-an" in text
    assert "BACKGROUND_HAS_AUDIO=\"no\"" in text


def test_script_uses_seamless_video_and_original_background_audio_for_long_form_copy_loop():
    text = script_text()

    assert "Long-form generation background file: $BACKGROUND_FILE" in text
    assert "Long-form rain audio file: $SOURCE_BACKGROUND_FILE" in text
    assert "-stream_loop -1 -i \"$BACKGROUND_FILE\"" in text
    assert "-i \"$SOURCE_BACKGROUND_FILE\"" in text
    assert "-c:v copy" in text
    assert "The video stream is looped and copied without FFmpeg video filters or re-encoding." in text

def test_script_logs_split_video_and_rain_audio_sources_and_volumes():
    text = script_text()

    assert "video source: background_seamless.mp4" in text
    assert "rain audio source: background.mp4" in text
    assert "rain audio stream detected: $BACKGROUND_HAS_AUDIO" in text
    assert "background_audio_volume=$BACKGROUND_AUDIO_VOLUME" in text
    assert "bgm_volume=$BGM_VOLUME" in text
