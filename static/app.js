const $ = (id) => document.getElementById(id);
let currentJobId = null;
let pollTimer = null;

async function pollStatus() {
  if (!currentJobId) return;
  const res = await fetch(`/status/${currentJobId}`);
  const data = await res.json();

  $("progress").value = data.progress || 0;
  $("progress-text").textContent = `生成中... ${data.progress || 0}%`;

  if (data.status === "done") {
    clearInterval(pollTimer);
    currentJobId = null;
    $("go").disabled = false;
    $("stop").disabled = true;
    $("result").hidden = false;
    $("title").textContent = data.title;
    $("meta").textContent = `${data.resolution} / ${Math.round(data.duration_sec / 60)}分 / BG:${data.background_image} / BGM:${data.bgm_file}`;
    $("dl").href = data.download_url;
  } else if (["error", "stopped"].includes(data.status)) {
    clearInterval(pollTimer);
    currentJobId = null;
    $("go").disabled = false;
    $("stop").disabled = true;
    $("error").hidden = false;
    $("error-detail").textContent = data.error || "生成に失敗しました";
  }
}

$("go").onclick = async () => {
  $("go").disabled = true;
  $("stop").disabled = false;
  $("result").hidden = true;
  $("error").hidden = true;
  $("progress-wrap").hidden = false;
  $("progress").value = 0;
  $("progress-text").textContent = "ジョブ起動中...";

  const payload = {
    duration_min: Number($("duration").value || 1),
    rain_intensity: Number($("rain").value || 0.55),
    vhs_strength: Number($("vhs").value || 0.45),
    color_tone: $("tone").value,
  };

  try {
    const res = await fetch('/generate', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || '生成失敗');
    currentJobId = body.job_id;
    pollTimer = setInterval(pollStatus, 1000);
  } catch (e) {
    $("go").disabled = false;
    $("stop").disabled = true;
    $("error").hidden = false;
    $("error-detail").textContent = e.message;
  }
};

$("stop").onclick = async () => {
  if (!currentJobId) return;
  await fetch(`/stop/${currentJobId}`, { method: 'POST' });
};
