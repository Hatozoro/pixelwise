from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import joblib
import os
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "digit_classifier_v1.pkl")

model = None
try:
    model = joblib.load(MODEL_PATH)
    print("Modell erfolgreich geladen!")
except Exception as e:
    print(f"Fehler beim Laden: {e}")

DB_CONFIG = {
    "dbname": "pixelwise",
    "user": "pixelwise",
    "password": "pixelwise",
    "host": "localhost"
}

def get_db():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

class ClassifyRequest(BaseModel):
    pixels: list[float]
    target_label: int
    username: str = "Anonym"

class JuryVoteRequest(BaseModel):
    task_id: int
    vote: str
    validator_name: str

@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}

@app.post("/api/classify")
def classify(req: ClassifyRequest):
    if len(req.pixels) != 784:
        raise HTTPException(status_code=400, detail="Pixel-Array muss genau 784 Werte enthalten.")
    if model is None:
        raise HTTPException(status_code=503, detail="Modell nicht geladen.")

    pixel_array = np.array(req.pixels, dtype=np.float32).reshape(1, -1)
    proba = model.predict_proba(pixel_array)[0]
    predicted_label = int(np.argmax(proba))
    confidence = float(proba[req.target_label])

    if predicted_label == req.target_label:
        score_gained = round(confidence * 100)
    else:
        score_gained = 0

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, score, trust_score) VALUES (%s, %s, 50) ON CONFLICT (username) DO UPDATE SET score = users.score + %s",
                (req.username, score_gained, score_gained)
            )
            pixel_string = ",".join(str(int(p)) for p in req.pixels)
            cur.execute(
                "INSERT INTO jury_tasks (creator, predicted_label, target_label, pixels, status) VALUES (%s, %s, %s, %s, 'pending')",
                (req.username, predicted_label, req.target_label, pixel_string)
            )
        conn.commit()
    finally:
        conn.close()

    return {
        "predicted_digit": predicted_label,
        "target_digit": req.target_label,
        "confidence": round(confidence * 100, 2),
        "score_gained": score_gained,
        "correct": predicted_label == req.target_label
    }

@app.post("/api/jury/vote")
def jury_vote(req: JuryVoteRequest):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Trust-Score des Validators holen
            cur.execute("SELECT trust_score FROM users WHERE username = %s", (req.validator_name,))
            row = cur.fetchone()
            validator_trust = row["trust_score"] if row else 50

            # Task holen um Creator zu kennen
            cur.execute("SELECT creator, is_honeypot, expected_label FROM jury_tasks WHERE id = %s", (req.task_id,))
            task = cur.fetchone()
            if not task:
                raise HTTPException(status_code=404, detail="Task nicht gefunden.")

            creator = task["creator"]
            is_honeypot = task["is_honeypot"] if task["is_honeypot"] is not None else False
            expected_label = task["expected_label"]

            # Honeypot-Prüfung
            honeypot_penalty = False
            if is_honeypot and expected_label is not None:
                # "troll" ist die korrekte Antwort auf Quatsch-Honeypots (expected_label = -1)
                # "correct" ist die korrekte Antwort auf echte Honeypots
                correct_honeypot_vote = "troll" if expected_label == -1 else "correct"
                if req.vote != correct_honeypot_vote:
                    honeypot_penalty = True

            # Task als validiert markieren
            cur.execute(
                "UPDATE jury_tasks SET status = %s, validator = %s WHERE id = %s",
                (req.vote, req.validator_name, req.task_id)
            )

            # Validator bekommt +5 Score fürs Mitmachen
            # Trust-Score: steigt bei korrektem Honeypot, sinkt bei falschem
            if honeypot_penalty:
                # Trust halbieren, max 100
                cur.execute("""
                    UPDATE users SET trust_score = GREATEST(1, trust_score / 2)
                    WHERE username = %s
                """, (req.validator_name,))
                validator_xp = 0
            else:
                # Trust leicht erhöhen bei korrektem Honeypot oder normalem Vote
                trust_gain = 2 if is_honeypot else 0
                cur.execute("""
                    UPDATE users
                    SET score = score + 5,
                        trust_score = LEAST(100, trust_score + %s)
                    WHERE username = %s
                """, (trust_gain, req.validator_name))
                # Neuen User anlegen falls nicht vorhanden
                cur.execute("""
                    INSERT INTO users (username, score, trust_score)
                    VALUES (%s, 5, 50)
                    ON CONFLICT (username) DO NOTHING
                """, (req.validator_name,))
                validator_xp = 5

            # Troll-Vote: Creator verliert Punkte und Trust
            if req.vote == "troll":
                cur.execute("""
                    UPDATE users
                    SET score = GREATEST(0, score - 20),
                        trust_score = GREATEST(1, trust_score - 10)
                    WHERE username = %s
                """, (creator,))

        conn.commit()
    finally:
        conn.close()

    return {
        "status": "ok",
        "validator_trust": validator_trust,
        "honeypot_penalty": honeypot_penalty,
        "validator_xp": validator_xp
    }

@app.get("/api/leaderboard")
def leaderboard():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT username, score, trust_score FROM users ORDER BY score DESC LIMIT 20")
            return cur.fetchall()
    finally:
        conn.close()

@app.get("/api/jury/task")
def jury_task(username: str = ""):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 30% Chance auf Honeypot falls welche verfügbar
            cur.execute(
                "SELECT id, creator, target_label, predicted_label, pixels, is_honeypot FROM jury_tasks WHERE status = 'pending' AND is_honeypot = TRUE LIMIT 1"
            )
            honeypot = cur.fetchone()

            import random
            if honeypot and random.random() < 0.3:
                return honeypot

            # Sonst normaler Task
            cur.execute(
                "SELECT id, creator, target_label, predicted_label, pixels, is_honeypot FROM jury_tasks WHERE status = 'pending' AND creator != %s AND (is_honeypot IS NULL OR is_honeypot = FALSE) LIMIT 1",
                (username,)
            )
            row = cur.fetchone()
            if row is None:
                return None
            return row
    finally:
        conn.close()
