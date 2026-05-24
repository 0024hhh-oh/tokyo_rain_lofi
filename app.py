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

    target_seconds = duration_min * 60
    width, height, fps = 1280, 720, 30

    # 生成成功最優先の最小構成（段階復帰しやすいよう将来拡張ポイントを保持）
    minimal_safe_mode = True

    cmd = ["ffmpeg", "-y", "-progress", "pipe:1", "-nostats"]

    bg = None
    bgm = None
    base_color = {"cool": "0x111827", "neutral": "0x1f2937", "warm": "0x2d1f17"}.get(color_tone, "0x111827")
    cmd += ["-f", "lavfi", "-i", f"color=c={base_color}:s={width}x{height}:r={fps}:d={target_seconds}"]
    cmd += ["-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=44100:duration={target_seconds}"]

    # NOTE: 演出（rain/VHS/zoom/drawtext）は一旦全停止。
    # 将来はminimal_safe_mode=Falseで段階的に戻せるよう、この分岐を拡張する。
    if minimal_safe_mode:
        cmd += ["-map", "0:v:0", "-map", "1:a:0"]

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
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    except Exception as exc:
        set_job(job_id, status="error", error=f"FFmpeg起動失敗: {exc}")
        return
    set_job(job_id, pid=proc.pid)

    stderr_lines = []
    try:
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("out_time_ms="):
                ms = int(line.split("=", 1)[1] or "0")
                p = int(clamp((ms / 1_000_000) / target_seconds * 100, 1, 99))
                set_job(job_id, progress=p)
        rc = proc.wait()
        if proc.stderr:
            stderr_lines = proc.stderr.read().splitlines()
        stderr_full = "\n".join(stderr_lines).strip()

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
