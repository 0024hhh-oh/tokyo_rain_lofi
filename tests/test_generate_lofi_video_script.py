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


def test_script_uses_original_rain_mp4_for_video_and_audio_loop_filter():
    text = script_text()

    assert '-stream_loop -1 -i "$BACKGROUND_FILE"' not in text
    assert '-i "$SOURCE_BACKGROUND_FILE"' in text
    assert '-f concat -safe 0 -i "$CONCAT_FILE"' in text
    assert "[1:a]atrim=0:{suno_total}" in text
    assert "volume={bgm_volume},apad,atrim=0:{total}[suno_bgm]" in text
    assert "[0:a]aresample=48000,asplit={loop_count}" in text
    assert "amix=inputs=2:duration=first" in text
    assert "amix=inputs=2:duration=shortest" not in text


def test_script_crossfades_rain_video_and_audio_at_each_loop_boundary():
    text = script_text()

    assert 'LOOP_CROSSFADE_SECONDS="${LOOP_CROSSFADE_SECONDS:-1}"' in text
    assert "loop_count = 1 if total <= duration else 1 + math.ceil" in text
    assert "offset = current_duration - crossfade" in text
    assert "xfade=transition=fade:duration={crossfade}:offset={offset}" in text
    assert "acrossfade=d={crossfade}:c1=tri:c2=tri" in text
    assert "required duration > {crossfade}s" in text


def test_script_trims_final_video_and_keeps_edge_fades():
    text = script_text()

    assert 'VIDEO_EDGE_FADE_SECONDS="${VIDEO_EDGE_FADE_SECONDS:-1}"' in text
    assert "trim=0:{total},setpts=PTS-STARTPTS" in text
    assert "fade=t=in:st=0:d={edge_fade}" in text
    assert "fade=t=out:st={fade_out_start}:d={edge_fade}" in text
    assert "atrim=0:{total},asetpts=N/SR/TB,volume={background_volume}[background_audio]" in text
    assert "The final output is trimmed to VIDEO_TOTAL_SECONDS" in text


def test_script_supports_silent_rain_mp4_by_using_suno_audio_only():
    text = script_text()

    assert "BACKGROUND_HAS_AUDIO=\"no\"" in text
    assert "if has_audio == \"yes\":" in text
    assert "[1:a]atrim=0:{suno_total},asetpts=N/SR/TB,volume={bgm_volume},apad,atrim=0:{total},alimiter=limit={audio_limit}[audio_out]" in text


def test_script_uses_dynamic_filter_complex_for_final_render():
    text = script_text()

    assert "calculate_background_loop_plan" in text
    assert "build_loop_filter_complex" in text
    assert "FILTER_COMPLEX=\"$(build_loop_filter_complex" in text
    assert '-filter_complex "$FILTER_COMPLEX"' in text
    assert '-map "[vout]" -map "[audio_out]"' in text
    assert '-c:v libx264 -preset "$LOOP_PRESET" -crf "$LOOP_CRF" -pix_fmt yuv420p' in text


def test_script_logs_split_video_and_rain_audio_sources_and_volumes():
    text = script_text()

    assert "video source: $SOURCE_BACKGROUND_FILE" in text
    assert "rain audio source: $SOURCE_BACKGROUND_FILE" in text
    assert "rain audio stream detected: $BACKGROUND_HAS_AUDIO" in text
    assert "background_audio_volume=$BACKGROUND_AUDIO_VOLUME" in text
    assert "bgm_volume=$BGM_VOLUME" in text
    assert "background_loop_count=$BACKGROUND_LOOP_COUNT" in text
    assert "loop_offset_seconds=$BACKGROUND_LOOP_OFFSET_SECONDS" in text
