import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from youtube_titles import generate_youtube_title, scene_label


def test_night_title_uses_folder_and_background_metadata():
    title = generate_youtube_title(
        "night",
        "batch_041_Oji_station",
        ["background_rainy_platform.png", "thumbnail.jpg", "01.mp3"],
    )
    assert title == (
        "【Playlist】Tokyo Rainy Night Memories | Oji station — "
        "rainy platform【LOFI】【CHILL】【BGM】"
    )


def test_day_title_preserves_existing_channel_style_without_number():
    title = generate_youtube_title("day", "Kameido backstreet", ["background.png"])
    assert title == "【Playlist】Tokyo Memory Archive | Kameido backstreet【LOFI】【CHILL】【BGM】"


def test_generic_folder_falls_back_to_descriptive_image_name():
    assert scene_label("Batch25", ["Arakicho_after_rain.jpg"]) == "Arakicho after rain"


def test_generic_metadata_uses_series_only():
    title = generate_youtube_title("night", "Batch25", ["background.png"])
    assert title == "【Playlist】Tokyo Rainy Night Memories【LOFI】【CHILL】【BGM】"


def test_title_is_limited_to_100_characters():
    title = generate_youtube_title("day", "x" * 200, ["background.png"])
    assert len(title) == 100
    assert title.endswith("【LOFI】【CHILL】【BGM】")


def test_invalid_mode_is_rejected():
    with pytest.raises(ValueError):
        generate_youtube_title("evening", "Oji", [])
