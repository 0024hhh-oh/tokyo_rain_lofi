#!/usr/bin/env python3
"""Repair only Drive copy-UUID leakage in videos uploaded by recent Actions runs."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import urllib.request
import zipfile

from youtube_titles import COPY_ID_PATTERN, clean_copy_ids


def clean_metadata(title, description):
    if not title.startswith(("【Playlist】Tokyo Rainy Night Memories", "【Playlist】Tokyo Memory Archive")):
        return title, description
    if not COPY_ID_PATTERN.search(title + "\n" + description):
        return title, description
    title = clean_copy_ids(title)
    title = re.sub(r"\s*\|\s*(?=【LOFI】)", "", title)
    description = clean_copy_ids(description)
    description = re.sub(r"drifts through\s+on a rainy Tokyo night\.",
                         "drifts through the quiet streets of Tokyo on a rainy night.", description)
    description = re.sub(r"drifts through\s*, a fading memory", "drifts through a fading memory", description)
    return title, description


def recent_uploaded_ids():
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    base = f"https://api.github.com/repos/{repo}"

    def get(url):
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        return urllib.request.urlopen(request, timeout=60).read()

    runs = json.loads(get(base + "/actions/workflows/generate_lofi_video.yml/runs?per_page=10"))["workflow_runs"]
    ids = set()
    for run in runs:
        if run["status"] != "completed":
            raise RuntimeError("Production run is still active; wait for generation before repair")
        with zipfile.ZipFile(io.BytesIO(get(base + f"/actions/runs/{run['id']}/logs"))) as archive:
            for name in archive.namelist():
                if name.endswith(".txt"):
                    log = archive.read(name).decode("utf-8-sig", errors="replace")
                    ids.update(re.findall(r"video ID: ([A-Za-z0-9_-]{11})\b", log))
    return sorted(ids)


def repair_video(youtube, video_id, apply=False, backup_dir=Path("metadata-backups")):
    items = youtube.videos().list(part="snippet", id=video_id).execute().get("items", [])
    if len(items) != 1:
        raise RuntimeError(f"Cannot read video metadata: {video_id}")
    original = items[0]["snippet"]
    title, description = clean_metadata(original["title"], original.get("description", ""))
    if (title, description) == (original["title"], original.get("description", "")):
        print(f"Unchanged: {video_id}")
        return False
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / f"{video_id}.json").write_text(json.dumps(items[0], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Repair title: {video_id}: {original['title']} -> {title}")
    if apply:
        fields = ("title", "description", "categoryId", "tags", "defaultLanguage", "defaultAudioLanguage")
        snippet = {key: original[key] for key in fields if key in original}
        snippet.update(title=title, description=description)
        youtube.videos().update(part="snippet", body={"id": video_id, "snippet": snippet}).execute()
        verified = youtube.videos().list(part="snippet", id=video_id).execute()["items"][0]["snippet"]
        if any(verified.get(key) != value for key, value in snippet.items()):
            raise RuntimeError(f"Metadata verification failed: {video_id}")
        print(f"Verified repaired title and description: https://www.youtube.com/watch?v={video_id}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", action="append", default=[])
    parser.add_argument("--recent-runs", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    ids = set(args.video_id)
    if args.recent_runs:
        ids.update(recent_uploaded_ids())
    if not ids:
        raise RuntimeError("No uploaded videos found")
    from upload_youtube_video import get_youtube_service
    youtube = get_youtube_service()
    changed = sum(repair_video(youtube, video_id, args.apply) for video_id in sorted(ids))
    print(f"Metadata repair summary: checked={len(ids)} changed={changed} apply={args.apply}")
