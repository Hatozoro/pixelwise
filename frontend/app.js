const canvas = document.getElementById("pad");
const ctx = canvas.getContext("2d");
let drawing = false;
let currentTargetDigit;
let timerInterval;
let timeLeft = 15;

ctx.lineWidth = 16;
ctx.lineCap = "round";
ctx.strokeStyle = "#000000";

canvas.addEventListener("mousedown", () => drawing = true);
canvas.addEventListener("mouseup", () => { drawing = false; ctx.beginPath(); });
canvas.addEventListener("mousemove", draw);

function draw(e) {
    if (!drawing) return;
    const rect = canvas.getBoundingClientRect();
    ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
}

document.getElementById("clear").addEventListener("click", () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    document.getElementById("result").textContent = "";
});

function startNewRound() {
    clearInterval(timerInterval);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    currentTargetDigit = Math.floor(Math.random() * 10);
    document.getElementById("target-digit").textContent = currentTargetDigit;
    
    timeLeft = 15;
    document.getElementById("timer-display").textContent = timeLeft;
    
    timerInterval = setInterval(() => {
        timeLeft--;
        document.getElementById("timer-display").textContent = timeLeft;
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            document.getElementById("result").style.color = "#dc3545";
            document.getElementById("result").textContent = "Zeit abgelaufen! Neue Zahl generiert.";
            startNewRound();
        }
    }, 1000);
}

document.getElementById("classify").addEventListener("click", async () => {
    const username = document.getElementById("username").value || "Anonymous";
    
    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = 28;
    tempCanvas.height = 28;
    const tempCtx = tempCanvas.getContext("2d");
    tempCtx.drawImage(canvas, 0, 0, 28, 28);
    
    const imgData = tempCtx.getImageData(0, 0, 28, 28);
    const pixels = [];
    let hasDrawnSomething = false;
    
    for (let i = 0; i < imgData.data.length; i += 4) {
        const alpha = imgData.data[i + 3] / 255.0;
        pixels.push(alpha);
        if (alpha > 0) hasDrawnSomething = true;
    }

    if (!hasDrawnSomething) {
        document.getElementById("result").style.color = "#dc3545";
        document.getElementById("result").textContent = "Bitte zeichne zuerst eine Ziffer!";
        return;
    }

    try {
        const response = await fetch("/api/classify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: username,
                pixels: pixels,
                target_label: currentTargetDigit
            })
        });
        
        if (!response.ok) throw new Error("Server-Fehler " + response.status);
        const data = await response.json();
        
        document.getElementById("result").style.color = "#28a745";
        document.getElementById("result").textContent = `Ergebnis: ${data.prediction} (Score +${data.points_earned})`;
        
        loadLeaderboard();
        loadJuryTask();
        startNewRound();
    } catch (err) {
        document.getElementById("result").style.color = "#dc3545";
        document.getElementById("result").textContent = "Fehler beim Verarbeiten der Daten";
    }
});

async function loadLeaderboard() {
    try {
        const res = await fetch("/api/leaderboard");
        const data = await res.json();
        const list = document.getElementById("leaderboard-list");
        list.innerHTML = "";
        data.forEach(user => {
            list.innerHTML += `<li><span>${user.username}</span><strong>${user.score} Pkt (Trust: ${user.trust_score})</strong></li>`;
        });
    } catch (e) {}
}

async function loadJuryTask() {
    try {
        const res = await fetch("/api/jury/task");
        const jCanvas = document.getElementById("jury-pad");
        const jCtx = jCanvas.getContext("2d");
        jCtx.clearRect(0, 0, jCanvas.width, jCanvas.height);

        if (res.status === 204) {
            document.getElementById("jury-prediction").textContent = "Keine Aufgaben vorhanden";
            return;
        }
        const data = await res.json();
        document.getElementById("jury-prediction").textContent = data.predicted_label;
        document.getElementById("jury-prediction-id").value = data.id;

        // Zeichne das Bild aus den gelesenen Pixeldaten nach
        if (data.pixels && data.pixels.length === 784) {
            const imgData = jCtx.createImageData(28, 28);
            for (let i = 0; i < data.pixels.length; i++) {
                const alpha = Math.floor(data.pixels[i] * 255);
                const idx = i * 4;
                imgData.data[idx] = 0;         // R
                imgData.data[idx + 1] = 0;     // G
                imgData.data[idx + 2] = 0;     // B
                imgData.data[idx + 3] = alpha; // Alpha (Sichtbarkeit)
            }
            jCtx.putImageData(imgData, 0, 0);
        }
    } catch (e) {}
}

async function sendJuryVote(voteType) {
    const taskId = document.getElementById("jury-prediction-id").value;
    const username = document.getElementById("username").value || "Anonymous";
    if (!taskId) return;
    
    try {
        const res = await fetch("/api/jury/vote", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_id: taskId, vote: voteType, username: username })
        });
        await res.json();
        document.getElementById("jury-feedback").textContent = `Stimme als ${username} abgegeben: ${voteType}`;
        loadJuryTask();
        loadLeaderboard();
    } catch (e) {
        document.getElementById("jury-feedback").textContent = "Fehler beim Senden des Votes";
    }
}

document.getElementById("jury-correct").addEventListener("click", () => sendJuryVote("correct"));
document.getElementById("jury-incorrect").addEventListener("click", () => sendJuryVote("incorrect"));
document.getElementById("jury-troll").addEventListener("click", () => sendJuryVote("troll"));

loadLeaderboard();
loadJuryTask();
startNewRound();
