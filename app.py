import os
import random
import re
import shlex
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = (BASE_DIR / "outputs").resolve()
IMAGES_DIR = (BASE_DIR / "images").resolve()
AUDIO_DIR = (BASE_DIR / "audio").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

JOBS = {}
JOBS_LOCK = threading.Lock()
IMAGE_EXTS = (".png", ".jpg", ".jpeg")


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def safe_slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\-\s]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text[:80] or "tokyo-rain-lofi"


def auto_title(color_tone: str) -> str:
    prefixes = [
        "Midnight Drizzle",
        "Last Train Home",
        "Neon Rain Memoir",
        "Sleepless Platform",
        "Convenience Store Glow",
        "Tokyo 2AM Static",
    ]
    suffix = {
        "cool": "(Blue Hour)",
        "warm": "(Amber Haze)",
        "neutral": "(Grey Memory)",
    }.get(color_tone, "(Night Tape)")
    return f"{random.choice(prefixes)} {suffix}"


def list_media_files(directory: Path, exts: tuple[str, ...]) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(p.resolve() for p in directory.iterdir() if p.is_file() and p.suffix.lower() in exts)


def pick_background_image() -> Path:
    images = list_media_files(IMAGES_DIR, IMAGE_EXTS)
    if not images:
        raise FileNotFoundError(
            f"背景画像が見つかりません。{IMAGES_DIR} に .png / .jpg / .jpeg を入れてください。"
        )

    # Prefer the expected smoke-test file when present, so images/background01.png is deterministic.
    for image in images:
        if image.name.lower() == "background01.png":
            return image
    for image in images:
        if image.stem.lower() == "background01":
            return image
    return images[0]


def set_job(job_id: str, **updates):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(updates)


def build_ffmpeg_command(data: dict, out_path: Path, title: str):
    # Stability pass: always render exactly 60 seconds until the image-based graph is proven.
    target_seconds = 60
    rain_intensity = clamp(float(data.get("rain_intensity", 0.55)), 0.0, 1.0)
    vhs_strength = clamp(float(data.get("vhs_strength", 0.45)), 0.0, 1.0)

    width, height, fps = 1280, 720, 30
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    bg = pick_background_image().resolve()
    if not bg.exists() or bg.suffix.lower() not in IMAGE_EXTS:
        raise FileNotFoundError(f"背景画像を読み込めません: {bg}")

    # Minimal Windows-safe graph. Keep the real image visible first.
    # Effects are intentionally light so the source image cannot be blacked out.
    noise_strength = 2 + int(vhs_strength * 5)
    saturation = 0.88 + ((1.0 - rain_intensity) * 0.08)

    filter_complex = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"fps={fps},"
        "format=yuv420p,"
        f"eq=brightness=0.000:contrast=1.030:saturation={saturation:.3f},"
        f"noise=alls={noise_strength}:allf=t+u"
        "[vout];"
        "[1:a]lowpass=f=2400,highpass=f=180,volume=0.14[aout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-framerate", str(fps),
        "-i", str(bg),
        "-f", "lavfi",
        "-i", f"anoisesrc=color=pink:amplitude=0.20:sample_rate=44100:d={target_seconds}",
        "-t", str(target_seconds),
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        "-metadata", f"title={title}",
        str(out_path),
    ]
    return cmd, target_seconds, bg, None


def worker(job_id: str, cmd: list[str], target_seconds: int, filename: str, title: str, bg: Path | None, bgm: Path | None):
    argv_for_log = " ".join(shlex.quote(p) for p in cmd)
    set_job(
        job_id,
        status="running",
        progress=1,
        ffmpeg_argv=cmd,
        ffmpeg_command=argv_for_log,
        background_image=str(bg) if bg else None,
        background_image_name=bg.name if bg else None,
    )
    print("[FFMPEG argv]", cmd, flush=True)
    print("[FFMPEG command]", argv_for_log, flush=True)
    if bg:
        print("[FFMPEG background]", str(bg), flush=True)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            check=False,
        )
    except Exception as exc:
        set_job(job_id, status="error", error=f"FFmpeg起動失敗: {exc}")
        return

    output_path = (OUTPUT_DIR / filename).resolve()
    stderr_full = (result.stderr or "").strip()
    stdout_full = (result.stdout or "").strip()
    output_exists = output_path.exists()
    output_size = output_path.stat().st_size if output_exists else 0

    if result.returncode == 0 and output_exists and output_size > 0:
        set_job(
            job_id,
            status="done",
            progress=100,
            title=title,
            filename=filename,
            download_url=f"/download/{filename}",
            duration_sec=target_seconds,
            resolution="1280x720",
            output_size_bytes=output_size,
            output_path=str(output_path),
            background_image=str(bg) if bg else None,
            background_image_name=bg.name if bg else None,
            bgm_file=(bgm.name if bgm else "generated_pink_noise_rain_bed"),
            ffmpeg_returncode=result.returncode,
            ffmpeg_stderr=stderr_full,
        )
    else:
        set_job(
            job_id,
            status="error",
            progress=0,
            error="FFmpeg failed or output file was not created",
            ffmpeg_returncode=result.returncode,
            ffmpeg_stdout=(stdout_full or "(stdout empty)"),
            ffmpeg_stderr=(stderr_full or "(stderr empty)"),
            output_path=str(output_path),
            output_exists=output_exists,
            output_size_bytes=output_size,
            background_image=str(bg) if bg else None,
            background_image_name=bg.name if bg else None,
        )


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/generate")
def generate():
    try:
        data = request.get_json(force=True)
        title = auto_title(data.get("color_tone", "cool"))
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{stamp}_{safe_slug(title)}.mp4"
        out_path = (OUTPUT_DIR / filename).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd, target_seconds, bg, bgm = build_ffmpeg_command(data, out_path, title)
        job_id = uuid.uuid4().hex
        with JOBS_LOCK:
            JOBS[job_id] = {
                "status": "queued",
                "progress": 0,
                "created_at": time.time(),
                "background_image": str(bg) if bg else None,
                "background_image_name": bg.name if bg else None,
            }

        t = threading.Thread(target=worker, args=(job_id, cmd, target_seconds, filename, title, bg, bgm), daemon=True)
        t.start()
        return jsonify({
            "job_id": job_id,
            "status": "queued",
            "duration_sec": target_seconds,
            "background_image": str(bg) if bg else None,
            "background_image_name": bg.name if bg else None,
        })
    except Exception as e:
        return jsonify({
            "error": "動画生成に失敗しました",
            "detail": str(e),
            "images_dir": str(IMAGES_DIR),
            "supported_image_exts": list(IMAGE_EXTS),
        }), 500


@app.get("/status/<job_id>")
def status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    return jsonify(job)


@app.post("/stop/<job_id>")
def stop(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    # subprocess.run is used for Windows-stable generation, so there is no live pid to terminate.
    if job.get("status") == "running":
        return jsonify({"ok": False, "reason": "generation is running in a blocking FFmpeg process"}), 409
    return jsonify({"ok": False, "reason": "not running"})


@app.get("/download/<path:filename>")
def download(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
