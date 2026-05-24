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
OUTPUT_DIR = Path("outputs")
IMAGES_DIR = Path("images")
AUDIO_DIR = Path("audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

JOBS = {}
JOBS_LOCK = threading.Lock()


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
    return [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in exts]


def set_job(job_id: str, **updates):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(updates)


def build_ffmpeg_command(data: dict, out_path: Path, title: str):
    duration_min = clamp(int(data.get("duration_min", 1)), 1, 60)
    color_tone = data.get("color_tone", "cool")
    rain_intensity = clamp(float(data.get("rain_intensity", 0.55)), 0.0, 1.0)
    vhs_strength = clamp(float(data.get("vhs_strength", 0.45)), 0.0, 1.0)

    target_seconds = duration_min * 60
    width, height, fps = 1280, 720, 30

    cmd = ["ffmpeg", "-y", "-progress", "pipe:1", "-nostats"]

    bg = None
    bgm = None
    if color_tone == "warm":
        top_color, bottom_color = "0x1e1722", "0x3a261f"
    elif color_tone == "neutral":
        top_color, bottom_color = "0x131722", "0x202733"
    else:
        top_color, bottom_color = "0x0a1022", "0x182c46"

    cmd += ["-f", "lavfi", "-i", f"color=c={top_color}:s={width}x{height}:r={fps}:d={target_seconds}"]
    cmd += ["-f", "lavfi", "-i", f"color=c={bottom_color}:s={width}x{height}:r={fps}:d={target_seconds}"]
    cmd += ["-f", "lavfi", "-i", f"anoisesrc=color=white:amplitude=0.3:sample_rate=44100:d={target_seconds}"]
    cmd += ["-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=44100:duration={target_seconds}"]
    cmd += ["-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.2:sample_rate=44100:d={target_seconds}"]

    vhs_mix = 0.03 + vhs_strength * 0.12
    rain_mix = 0.015 + rain_intensity * 0.045
    lofi_mix = 0.07

    filter_complex = (
        "[0:v][1:v]blend=all_expr='A*(1-Y/H)+B*(Y/H)'[grad];"
        "[grad]drawbox=x=0:y=H*0.68:w=W:h=H*0.32:color=0x05070d@0.45:t=fill,"
        "drawbox=x=W*0.08:y=H*0.62:w=W*0.08:h=H*0.22:color=0xf2c572@0.20:t=fill,"
        "drawbox=x=W*0.20:y=H*0.58:w=W*0.05:h=H*0.26:color=0x9dc7ff@0.16:t=fill,"
        "drawbox=x=W*0.31:y=H*0.66:w=W*0.09:h=H*0.18:color=0xff8bb4@0.18:t=fill,"
        "drawbox=x=W*0.82:y=H*0.60:w=W*0.06:h=H*0.24:color=0xa0ffd6@0.14:t=fill,"
        "eq=contrast=1.08:brightness=-0.03:saturation=0.85[city];"
        "[2:v]format=gray,eq=contrast=1.6:brightness=-0.18[vnoise];"
        f"[city][vnoise]blend=all_mode=overlay:all_opacity={vhs_mix:.3f}[vout];"
        "[3:a]volume=0.10[a_lofi];"
        "[4:a]lowpass=f=2400,highpass=f=250,volume=0.20[a_rain];"
        f"[a_lofi][a_rain]amix=inputs=2:weights='{lofi_mix:.3f} {rain_mix:.3f}':normalize=0[aout]"
    )

    cmd += ["-filter_complex", filter_complex, "-map", "[vout]", "-map", "[aout]"]

    cmd += [
        "-t", str(target_seconds),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        "-metadata", f"title={title}",
        str(out_path),
    ]
    return cmd, target_seconds, bg, bgm


def worker(job_id: str, cmd: list[str], target_seconds: int, filename: str, title: str, bg: Path | None, bgm: Path | None):
    set_job(job_id, status="running", progress=1)
    print("[FFMPEG]", " ".join(shlex.quote(p) for p in cmd), flush=True)
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except Exception as exc:
        set_job(job_id, status="error", error=f"FFmpeg起動失敗: {exc}")
        return
    set_job(job_id, pid=proc.pid)

    stdout_accum = ""
    stderr_accum = ""
    consumed_lines = 0

    def update_progress(progress_text: str):
        nonlocal consumed_lines
        lines = progress_text.splitlines()
        new_lines = lines[consumed_lines:]
        consumed_lines = len(lines)
        for line in new_lines:
            line = line.strip()
            if line.startswith("out_time_ms="):
                ms = int(line.split("=", 1)[1] or "0")
                p = int(clamp((ms / 1_000_000) / target_seconds * 100, 1, 99))
                set_job(job_id, progress=p)

    try:
        while True:
            try:
                stdout_final, stderr_final = proc.communicate(timeout=1)
                stdout_accum = stdout_final or ""
                stderr_accum = stderr_final or ""
                update_progress(stdout_accum)
                break
            except subprocess.TimeoutExpired as timeout_exc:
                stdout_accum = timeout_exc.output or stdout_accum
                stderr_accum = timeout_exc.stderr or stderr_accum
                update_progress(stdout_accum)

        rc = proc.returncode
        stderr_full = stderr_accum.strip()

        if rc == 0:
            set_job(
                job_id,
                status="done",
                progress=100,
                title=title,
                filename=filename,
                download_url=f"/download/{filename}",
                duration_sec=target_seconds,
                resolution="1280x720",
                background_image=(bg.name if bg else "generated_color"),
                bgm_file=(bgm.name if bgm else "generated_tone"),
            )
        else:
            set_job(
                job_id,
                status="error",
                error=f"FFmpeg failed (returncode={rc})",
                ffmpeg_returncode=rc,
                ffmpeg_stderr=(stderr_full or "(stderr empty)"),
            )
    except Exception as exc:
        set_job(job_id, status="error", error=str(exc))


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
        out_path = OUTPUT_DIR / filename

        cmd, target_seconds, bg, bgm = build_ffmpeg_command(data, out_path, title)
        job_id = uuid.uuid4().hex
        with JOBS_LOCK:
            JOBS[job_id] = {"status": "queued", "progress": 0, "created_at": time.time()}

        t = threading.Thread(target=worker, args=(job_id, cmd, target_seconds, filename, title, bg, bgm), daemon=True)
        t.start()
        return jsonify({"job_id": job_id, "status": "queued"})
    except Exception as e:
        return jsonify({"error": "動画生成に失敗しました", "detail": str(e)}), 500


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
    pid = job.get("pid")
    if pid and job.get("status") == "running":
        try:
            os.kill(pid, 15)
            set_job(job_id, status="stopped", error="ユーザーが停止しました")
            return jsonify({"ok": True})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": False, "reason": "not running"})


@app.get("/download/<path:filename>")
def download(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
