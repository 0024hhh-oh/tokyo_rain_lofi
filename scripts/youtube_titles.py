#!/usr/bin/env python3
"""Deterministic YouTube title generation for Tokyo ChillMatic FM."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

TITLE_SUFFIX = "【LOFI】【CHILL】【BGM】"
TITLE_LIMIT = 100
DESCRIPTION_LIMIT = 5000
SERIES_BY_MODE = {
    "day": "Tokyo Memory Archive",
    "night": "Tokyo Rainy Night Memories",
}
MEDIA_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
    ".mov",
}
IGNORED_MEDIA_WORDS = {
    "background",
    "background loop",
    "thumbnail",
    "thumbnail source",
    "logo",
    "overlay",
    "mask",
    "light overlay",
}


def _humanize(value: str) -> str:
    value = Path(value).stem
    value = re.sub(r"^(?:batch|video|project)[ _-]*\d+[ _-]*", "", value, flags=re.I)
    value = re.sub(r"[_-]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .-|—")
    if not value:
        return ""
    folded = value.casefold()
    if folded in IGNORED_MEDIA_WORDS or re.fullmatch(
        r"(?:batch|video|project)?\s*\d+", folded
    ):
        return ""
    return value


def _background_label(file_names: Iterable[str]) -> str:
    preferred: list[str] = []
    fallback: list[str] = []
    for name in file_names:
        path = Path(name)
        if path.suffix.casefold() not in MEDIA_EXTENSIONS:
            continue
        label = _humanize(name)
        label = re.sub(
            r"^(?:background(?: loop)?|thumbnail source)\s*", "", label, flags=re.I
        ).strip()
        if not label:
            continue
        folded_name = path.stem.casefold()
        if folded_name.startswith(("thumbnail", "logo", "overlay", "mask", "light_overlay")):
            continue
        if folded_name.startswith("background"):
            preferred.append(label)
        else:
            fallback.append(label)
    candidates = preferred or fallback
    return sorted(candidates, key=str.casefold)[0] if candidates else ""


def scene_label(folder_name: str, file_names: Iterable[str]) -> str:
    """Build a stable scene label from folder metadata and background filename."""
    folder = _humanize(folder_name)
    background = _background_label(file_names)
    if folder and background and folder.casefold() != background.casefold():
        if folder.casefold() in background.casefold():
            return background
        if background.casefold() in folder.casefold():
            return folder
        return f"{folder} — {background}"
    return folder or background


def generate_youtube_title(mode: str, folder_name: str, file_names: Iterable[str]) -> str:
    """Return a YouTube-safe title of at most 100 characters."""
    try:
        series = SERIES_BY_MODE[mode.casefold()]
    except KeyError as exc:
        raise ValueError(f"Unsupported project mode: {mode}") from exc

    prefix = f"【Playlist】{series}"
    scene = scene_label(folder_name, file_names)
    separator = " | " if scene else ""
    available = TITLE_LIMIT - len(prefix) - len(separator) - len(TITLE_SUFFIX)
    if available < 0:
        raise ValueError("Fixed title components exceed YouTube's title limit")
    if len(scene) > available:
        scene = scene[: max(0, available - 1)].rstrip() + "…"
    return f"{prefix}{separator}{scene}{TITLE_SUFFIX}"


def generate_youtube_description(
    mode: str, folder_name: str, file_names: Iterable[str]
) -> str:
    """Return a stable channel description with one mode-specific scene line."""
    normalized_mode = mode.casefold()
    if normalized_mode not in SERIES_BY_MODE:
        raise ValueError(f"Unsupported project mode: {mode}")

    scene = scene_label(folder_name, file_names)
    if normalized_mode == "night":
        scene_line = (
            f"Tonight's broadcast drifts through {scene} on a rainy Tokyo night."
            if scene
            else "Tonight's broadcast drifts through the quiet streets of Tokyo on a rainy night."
        )
    else:
        scene_line = (
            f"Today's broadcast drifts through {scene}, a fading memory from somewhere in Tokyo."
            if scene
            else "Today's broadcast drifts through a fading memory from somewhere in Tokyo."
        )

    description = f"""Welcome to Tokyo ChillMatic FM.

A fictional radio station broadcasting memories from somewhere in Tokyo.

{scene_line}

Perfect for:

• Study
• Work
• Reading
• Relaxation
• Sleep

Tokyo ChillMatic FM is an ongoing archive of rainy streets, fading landscapes, forgotten places, and everyday memories.

Thank you for listening.

🎧 Tokyo ChillMatic FM

Broadcasting memories from somewhere in Tokyo.

#lofi
#chill
#rain
#tokyo
#studymusic
#sleepmusic"""
    if len(description) > DESCRIPTION_LIMIT:
        raise ValueError("Generated description exceeds YouTube's description limit")
    return description
