const EXAMPLES = {
  fake1: "BREAKING: The president was secretly replaced by a robot in 2020. Anonymous sources inside the White House confirm this shocking global conspiracy that mainstream media refuses to cover.",
  real1: "The Federal Reserve raised interest rates by 25 basis points on Wednesday following its latest two-day policy meeting, in line with expectations from Wall Street analysts.",
  fake2: "Scientists discover that drinking bleach mixed with lemon juice cures all diseases including cancer. The government and Big Pharma have been hiding this simple cure for decades.",
  real2: "Researchers at MIT have published new findings on quantum computing, demonstrating a 1000-qubit processor capable of solving optimization problems faster than classical computers."
};

let selectedFile = null;

function switchTab(tab) {
  document.querySelectorAll(".tab-panel").forEach(p => { p.classList.remove("active"); p.classList.add("hidden"); });
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  const panel = document.getElementById("tab-" + tab);
  panel.classList.add("active");
  panel.classList.remove("hidden");
  document.querySelectorAll(".tab-btn")[tab === "text" ? 0 : 1].classList.add("active");
}

function show(id) { document.getElementById(id).classList.remove("hidden"); }
function hide(id) { document.getElementById(id).classList.add("hidden"); }

function buildResultHTML(data) {
  const isReal = data.label === "REAL";
  const cls    = isReal ? "real" : "fake";
  const badge  = isReal ? "✅ REAL" : "❌ FAKE";
  const msg    = data.type === "text"
    ? (isReal ? "Cet article semble authentique." : "Cet article ressemble à une fake news.")
    : (isReal ? "Cette image semble réelle." : "Cette image semble générée par IA.");

  return `
    <div class="result-header">
      <span class="result-badge ${cls}">${badge}</span>
      <span class="result-confidence">Confiance : <strong>${data.confidence}%</strong></span>
    </div>
    <p style="font-size:14px;color:var(--muted);margin-bottom:14px;">${msg}</p>
    <div class="proba-row">
      <div class="proba-item">
        <label><span>REAL</span><span>${data.real_proba}%</span></label>
        <div class="proba-track"><div class="proba-fill real" style="width:${data.real_proba}%"></div></div>
      </div>
      <div class="proba-item">
        <label><span>FAKE</span><span>${data.fake_proba}%</span></label>
        <div class="proba-track"><div class="proba-fill fake" style="width:${data.fake_proba}%"></div></div>
      </div>
    </div>`;
}

async function analyzeText() {
  const text = document.getElementById("news-input").value.trim();
  if (text.length < 10) { alert("Minimum 10 caractères requis."); return; }
  hide("text-result");
  show("text-loader");
  try {
    const res  = await fetch("/predict_text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    const data = await res.json();
    if (data.error) { alert("Erreur : " + data.error); }
    else {
      data.type = "text";
      const box = document.getElementById("text-result");
      box.className = "result-box " + (data.label === "REAL" ? "real" : "fake");
      box.innerHTML = buildResultHTML(data);
      show("text-result");
    }
  } catch(e) { alert("Erreur de connexion au serveur."); }
  finally    { hide("text-loader"); }
}

function clearText()     { document.getElementById("news-input").value = ""; hide("text-result"); }
function setExample(key) { document.getElementById("news-input").value = EXAMPLES[key]; hide("text-result"); }

function handleImageUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  selectedFile = file;
  document.getElementById("img-preview").src = URL.createObjectURL(file);
  show("img-preview-container");
  hide("image-result");
}

function dragOver(e)  { e.preventDefault(); document.getElementById("drop-zone").classList.add("dragover"); }
function dragLeave(e) { document.getElementById("drop-zone").classList.remove("dragover"); }
function dropImage(e) {
  e.preventDefault();
  document.getElementById("drop-zone").classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (!file) return;
  selectedFile = file;
  document.getElementById("img-preview").src = URL.createObjectURL(file);
  show("img-preview-container");
  hide("image-result");
}

async function analyzeImage() {
  if (!selectedFile) { alert("Aucune image sélectionnée."); return; }
  hide("image-result");
  show("image-loader");
  const formData = new FormData();
  formData.append("image", selectedFile);
  try {
    const res  = await fetch("/predict_image", { method: "POST", body: formData });
    const data = await res.json();
    if (data.error) { alert("Erreur : " + data.error); }
    else {
      data.type = "image";
      const box = document.getElementById("image-result");
      box.className = "result-box " + (data.label === "REAL" ? "real" : "fake");
      box.innerHTML = buildResultHTML(data);
      show("image-result");
    }
  } catch(e) { alert("Erreur de connexion au serveur."); }
  finally    { hide("image-loader"); }
}

function clearImage() {
  selectedFile = null;
  document.getElementById("img-preview").src = "";
  document.getElementById("img-input").value = "";
  hide("img-preview-container");
  hide("image-result");
}

// Ctrl+Enter pour analyser le texte
document.addEventListener("keydown", function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    if (document.getElementById("tab-text").classList.contains("active")) analyzeText();
  }
});
