import os
import random
import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory, jsonify

app = Flask(__name__)
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


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


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/generate")
def generate():
    data = request.get_json(force=True)

    duration_min = clamp(int(data.get("duration_min", 5)), 1, 60)
    rain_intensity = clamp(float(data.get("rain_intensity", 0.5)), 0.0, 1.0)
    vhs_strength = clamp(float(data.get("vhs_strength", 0.4)), 0.0, 1.0)
    color_tone = data.get("color_tone", "cool")
    force_5m_loop = bool(data.get("force_5m_loop", True))

    target_seconds = 300 if force_5m_loop else duration_min * 60
    clip_seconds = 10

    width, height = 1280, 720

    title = auto_title(color_tone)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{stamp}_{safe_slug(title)}.mp4"
    out_path = OUTPUT_DIR / filename

    # Visual recipe: dark Tokyo-like atmosphere from generated layers
    base_hue = {"cool": "0.95", "warm": "1.05", "neutral": "1.0"}.get(color_tone, "1.0")
    sat = {"cool": "0.78", "warm": "0.72", "neutral": "0.68"}.get(color_tone, "0.72")

    noise = 4 + int(vhs_strength * 16)
    vignette = 0.35 + vhs_strength * 0.35
    glitch_shift = 1 + int(vhs_strength * 4)
    rain_alpha = 0.05 + rain_intensity * 0.18
    rain_speed = 1.2 + rain_intensity * 2.2

    # Generate a 10-second loopable scene then loop it to target duration
    filtergraph = (
        f"color=c=0x0b0f18:s={width}x{height}:d={clip_seconds}[bg];"
        f"color=c=0x1a2538:s={width}x{height}:d={clip_seconds},"
        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(gt(mod(X+Y*T*{rain_speed:.2f},70),66),255*{rain_alpha:.3f},0)'[rain];"
        f"[bg][rain]overlay=shortest=1[tmp1];"
        f"[tmp1]noise=alls={noise}:allf=t+u,"
        f"eq=brightness=-0.08:contrast=1.05:saturation={sat},"
        f"colorchannelmixer=rr={base_hue}:gg=1.0:bb=0.95,"
        f"vignette=PI/{2+vignette:.2f},"
        f"split=3[r][g][b];"
        f"[r]crop=iw-{glitch_shift}:ih:{glitch_shift}:0[r2];"
        f"[g]crop=iw:ih:0:0[g2];"
        f"[b]crop=iw-{glitch_shift}:ih:0:0[b2];"
        f"[r2][g2][b2]mergeplanes=0x001020:yuv444p,format=yuv420p[v]"
    )

    # base rain ambience using anoisesrc (no external assets required)
    volume = 0.04 + rain_intensity * 0.10
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        filtergraph,
        "-f",
        "lavfi",
        "-i",
        f"anoisesrc=color=pink:amplitude={volume:.3f}:d={clip_seconds}",
        "-shortest",
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
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(OUTPUT_DIR / "_base_loop.mp4"),
    ]
    subprocess.run(cmd, check=True)

    loop_count = max(1, target_seconds // clip_seconds)
    concat_txt = OUTPUT_DIR / "_concat.txt"
    with concat_txt.open("w", encoding="utf-8") as f:
        for _ in range(loop_count):
            f.write(f"file '{(OUTPUT_DIR / '_base_loop.mp4').resolve()}'\n")

    concat_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_txt),
        "-c",
        "copy",
        str(out_path),
    ]
    subprocess.run(concat_cmd, check=True)

    return jsonify(
        {
            "title": title,
            "filename": filename,
            "download_url": f"/download/{filename}",
            "duration_sec": loop_count * clip_seconds,
            "resolution": "1280x720",
        }
    )


@app.get("/download/<path:filename>")
def download(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=False)
