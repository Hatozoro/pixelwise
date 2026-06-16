const API_KEY = "REPLACE_ME"; // Wird beim Deploy überschrieben
const N = 28; const SCALE = 10; 

const pad = document.getElementById("pad");
const view = pad.getContext("2d");
view.imageSmoothingEnabled = false; 

const grid = document.createElement("canvas");
grid.width = N; grid.height = N;
const gctx = grid.getContext("2d");
gctx.lineWidth = 2.5;
gctx.lineCap = "round"; gctx.lineJoin = "round";
let drawing = false;

// Haupt Variablen für das Spielprinzip
let currentTargetDigit = 5;
let timeLeft = 30;
let timerInterval = null;

function render() {
    view.drawImage(grid, 0, 0, pad.width, pad.height);
}

function clearPad() {
    gctx.fillStyle = "#fff";
    gctx.fillRect(0, 0, N, N);
    render();
}
clearPad();

pad.onmousedown = e => {
    drawing = true; gctx.beginPath();
    gctx.moveTo(e.offsetX / SCALE, e.offsetY / SCALE);
};
pad.onmousemove = e => {
    if (!drawing) return;
    gctx.lineTo(e.offsetX / SCALE, e.offsetY / SCALE);
    gctx.stroke(); render();
};
pad.onmouseup = pad.onmouseleave = () => { drawing = false; };

function getPixels() {
    const data = gctx.getImageData(0, 0, N, N).data;
    const pixels = [];
    for (let y = 0; y < N; y++) {
        const row = [];
        for (let x = 0; x < N; x++) {
            row.push(255 - data[(y * N + x) * 4]);
        }
        pixels.push(row);
    }
    return pixels;
}

// Startet eine neue Runde im Creator Modus mit random Zahl/Ziffer
function startNewRound() {
    currentTargetDigit = Math.floor(Math.random() * 10);
    document.getElementById("target-digit").textContent = currentTargetDigit;
    timeLeft = 30;
    document.getElementById("timer-display").textContent = timeLeft;
    
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        timeLeft--;
        document.getElementById("timer-display").textContent = timeLeft;
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            classify(); 
        }
    }, 1000);
    clearPad();
}

async function classify() {
    const username = document.getElementById("username").value || "User1";
    const r = await fetch("/api/classify", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        },
        body: JSON.stringify({ 
            pixels: getPixels(),
            username: username,
            target_label: currentTargetDigit
        })
    });
    const out = document.getElementById("result");
    if (!r.ok) { out.textContent = "Error " + r.status; return; }
    const d = await r.json();
    out.textContent = `Prediction: ${d.prediction} (${(d.confidence * 100).toFixed(1)}%)`;
    
    refreshLeaderboard();
    setTimeout(startNewRound, 2000); 
}

async function refreshLeaderboard() {
    const r = await fetch("/api/leaderboard");
    if (!r.ok) return;
    const list = document.getElementById("leaderboard-list");
    list.innerHTML = "";
    const data = await r.json();
    data.forEach(user => {
        const li = document.createElement("li");
        li.textContent = `${user.username}: ${user.score} Punkte (Trust Score: ${user.trust_score}%)`;
        list.appendChild(li);
    });
}

async function fetchJuryTask() {
    const r = await fetch("/api/jury/task");
    if (!r.ok) return;
    const d = await r.json();
    if (d.error) {
        document.getElementById("jury-prediction").textContent = "Keine Aufgaben vorhanden";
        return;
    }
    document.getElementById("jury-prediction").textContent = d.prediction;
    document.getElementById("jury-prediction-id").value = d.prediction_id;
}

async function submitJuryReview(isCorrect) {
    const username = document.getElementById("username").value || "User1";
    const predictionId = document.getElementById("jury-prediction-id").value;
    if (!predictionId) return;

    const r = await fetch("/api/jury/submit", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-API-Key": API_KEY
        },
        body: JSON.stringify({
            username: username,
            prediction_id: parseInt(predictionId),
            is_correct: isCorrect
        })
    });
    
    if (r.ok) {
        const d = await r.json();
        document.getElementById("jury-feedback").textContent = `Wertung gesendet. Neuer Trust Score: ${d.new_trust_score}%`;
        refreshLeaderboard();
        fetchJuryTask();
    }
}

document.getElementById("classify").onclick = classify;
document.getElementById("clear").onclick = () => {
    clearPad();
    document.getElementById("result").textContent = "";
};

document.getElementById("jury-correct").onclick = () => submitJuryReview(true);
document.getElementById("jury-troll").onclick = () => submitJuryReview(false);

// Initialer Start wenn man die Seite ladet
startNewRound();
refreshLeaderboard();
fetchJuryTask();
