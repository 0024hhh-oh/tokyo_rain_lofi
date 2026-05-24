const $ = (id) => document.getElementById(id);

$("go").onclick = async () => {
  const btn = $("go");
  btn.disabled = true;
  btn.textContent = "生成中...（約20-60秒）";

  try {
    const payload = {
      duration_min: Number($("duration").value || 5),
      rain_intensity: Number($("rain").value || 0.5),
      vhs_strength: Number($("vhs").value || 0.4),
      color_tone: $("tone").value,
      force_5m_loop: $("loop5").checked,
    };

    const res = await fetch('/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("生成に失敗しました");
    const data = await res.json();

    $("result").hidden = false;
    $("title").textContent = data.title;
    $("meta").textContent = `${data.resolution} / ${Math.round(data.duration_sec/60)}分 / MP4`;
    $("dl").href = data.download_url;
  } catch (e) {
    alert(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "🎬 生成する";
  }
};
