import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from youtube_titles import (
    generate_youtube_description,
    generate_youtube_title,
    scene_label,
)


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


def test_night_description_contains_scene_and_existing_channel_structure():
    description = generate_youtube_description(
        "night", "batch_041_Oji_station", ["background_rainy_platform.png"]
    )
    assert "Tonight's broadcast drifts through Oji station — rainy platform" in description
    assert "• Study\n• Work\n• Reading\n• Relaxation\n• Sleep" in description
    assert description.endswith("#sleepmusic")


def test_day_description_uses_day_language():
    description = generate_youtube_description("day", "Kameido backstreet", ["background.png"])
    assert (
        "Today's broadcast drifts through Kameido backstreet, "
        "a fading memory from somewhere in Tokyo."
    ) in description
    assert len(description) <= 5000
