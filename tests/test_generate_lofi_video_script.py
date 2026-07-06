from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_lofi_video.sh"


def script_text() -> str:
    return SCRIPT.read_text()


def test_script_uses_suno_total_duration_instead_of_fixed_target_seconds():
    text = script_text()

    assert "TARGET_SECONDS" not in text
    assert "TOTAL_SECONDS" in text
    assert "ffprobe" in text
    assert "total += duration" in text
    assert "-t \"$TOTAL_SECONDS\"" in text


def test_script_loops_background_but_not_suno_concat_input():
    text = script_text()

    assert '-stream_loop -1 -i "$BACKGROUND_FILE"' in text
    assert '-stream_loop -1 -f concat' not in text
    assert '-f concat -safe 0 -i "$CONCAT_FILE"' in text
    assert "amix=inputs=2:duration=shortest" in text
