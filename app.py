import os
import random
import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

app = Flask(__name__)
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


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


def run_ffmpeg(cmd):
    print("[FFMPEG]", " ".join(shlex.quote(part) for part in cmd), flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("[FFMPEG][STDERR]\n" + proc.stderr, flush=True)
        raise RuntimeError(
            "FFmpeg failed with exit code "
            f"{proc.returncode}\n"
            f"Command: {' '.join(shlex.quote(part) for part in cmd)}\n"
            f"STDERR:\n{proc.stderr.strip()}"
        )
    return proc


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/generate")
def generate():
    try:
        data = request.get_json(force=True)

        duration_min = clamp(int(data.get("duration_min", 5)), 1, 60)
        rain_intensity = clamp(float(data.get("rain_intensity", 0.5)), 0.0, 1.0)
        color_tone = data.get("color_tone", "cool")

        # まず確実に生成できる最小構成: 1分固定MP4
        target_seconds = 60
        width, height = 1280, 720
        fps = 30

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        title = auto_title(color_tone)
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{stamp}_{safe_slug(title)}.mp4"
        out_path = OUTPUT_DIR / filename

        hue = {"cool": "0.92", "warm": "1.08", "neutral": "1.00"}.get(color_tone, "1.00")
        sat = {"cool": "0.85", "warm": "0.80", "neutral": "0.75"}.get(color_tone, "0.80")
        noise = 3 + int(rain_intensity * 5)

        # filter_complex を明示し、壊れやすい演出は簡略化
        filter_complex = (
            f"[0:v]"
            f"eq=brightness=-0.06:contrast=1.05:saturation={sat},"
            f"colorchannelmixer=rr={hue}:gg=1.0:bb=0.95,"
            f"noise=alls={noise}:allf=t+u,"
            f"format=yuv420p[v]"
        )

        volume = 0.02 + rain_intensity * 0.08

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x111827:s={width}x{height}:r={fps}:d={target_seconds}",
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=pink:amplitude={volume:.3f}:d={target_seconds}",
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "24",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
        run_ffmpeg(cmd)

        return jsonify(
            {
                "title": title,
                "filename": filename,
                "download_url": f"/download/{filename}",
                "duration_sec": target_seconds,
                "resolution": f"{width}x{height}",
                "note": "安定化のため現在は1分固定で生成します。",
                "requested_duration_min": duration_min,
            }
        )
    except Exception as e:
        return jsonify({"error": "動画生成に失敗しました", "detail": str(e)}), 500


@app.get("/download/<path:filename>")
def download(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
