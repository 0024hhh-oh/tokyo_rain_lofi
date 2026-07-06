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
    assert "[1:a]atrim=0:${SUNO_TOTAL_SECONDS}" in text
    assert "[0:a]atrim=0:${VIDEO_TOTAL_SECONDS}" in text
    assert "amix=inputs=2:duration=longest" in text
    assert "amix=inputs=2:duration=shortest" not in text
