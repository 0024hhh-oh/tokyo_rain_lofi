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
    rain_intensity = clamp(float(data.get("rain_intensity", 0.55)), 0.0, 1.0)
    vhs_strength = clamp(float(data.get("vhs_strength", 0.45)), 0.0, 1.0)
    color_tone = data.get("color_tone", "cool")

    target_seconds = duration_min * 60
    width, height, fps = 1280, 720, 30

    images = list_media_files(IMAGES_DIR, (".jpg", ".jpeg", ".png", ".webp"))
    bg = random.choice(images) if images else None

    bgm_files = list_media_files(AUDIO_DIR, (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"))
    bgm = random.choice(bgm_files) if bgm_files else None

    hue = {"cool": "0.92", "warm": "1.08", "neutral": "1.00"}.get(color_tone, "1.00")
    sat = {"cool": "0.82", "warm": "0.78", "neutral": "0.74"}.get(color_tone, "0.80")
    noise = 2 + int(vhs_strength * 8)

    v_filters = [
        f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
        "fps=30",
        "zoompan=z='min(1.08,zoom+0.00008)':d=1:x='iw/2-(iw/zoom/2)+sin(on/250)*10':y='ih/2-(ih/zoom/2)+cos(on/280)*8':s=1280x720",
        f"eq=brightness=-0.06:contrast=1.08:saturation={sat}",
        f"colorchannelmixer=rr={hue}:gg=1.0:bb=0.95",
        "curves=all='0/0 0.35/0.28 0.7/0.78 1/1'",
        f"noise=alls={noise}:allf=t+u",
        "drawbox=x=0:y=0:w=iw:h=34:color=black@0.35:t=fill",
        "drawtext=text='TOKYO RAIN LOFI':x=24:y=8:fontsize=18:fontcolor=white@0.80",
        "format=yuv420p",
    ]

    cmd = ["ffmpeg", "-y", "-progress", "pipe:1", "-nostats"]

    if bg:
        cmd += ["-loop", "1", "-i", str(bg)]
    else:
        cmd += ["-f", "lavfi", "-i", f"color=c=0x111827:s={width}x{height}:r={fps}:d={target_seconds}"]

    if bgm:
        cmd += ["-stream_loop", "-1", "-i", str(bgm)]
    else:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=44100:duration={target_seconds}"]

    cmd += ["-f", "lavfi", "-i", f"anoisesrc=color=white:amplitude={0.04 + rain_intensity * 0.12:.3f}:d={target_seconds}"]

    filter_complex = (
        f"[0:v]{','.join(v_filters)}[v];"
        f"[1:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,volume=0.26[bgm];"
        f"[2:a]highpass=f=200,lowpass=f=7000,volume={0.45 + rain_intensity * 0.35:.2f}[rain];"
        "[bgm][rain]amix=inputs=2:duration=first:dropout_transition=2[a]"
    )

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-t", str(target_seconds),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
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
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    except Exception as exc:
        set_job(job_id, status="error", error=f"FFmpeg起動失敗: {exc}")
        return
    set_job(job_id, pid=proc.pid)

    try:
        for line in proc.stdout:
            line = line.strip()
            if line.startswith("out_time_ms="):
                ms = int(line.split("=", 1)[1] or "0")
                p = int(clamp((ms / 1_000_000) / target_seconds * 100, 1, 99))
                set_job(job_id, progress=p)
        rc = proc.wait()

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
            set_job(job_id, status="error", error="FFmpeg failed")
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
