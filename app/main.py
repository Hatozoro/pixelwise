from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
import random
from app.classifier import classify_batch
from app.models import Prediction, User, SessionLocal

class ClassifyRequest(BaseModel):
    pixels: list[list[int]]
    username: str
    target_label: int

class ClassifyResponse(BaseModel):
    prediction: str
    confidence: float
    scores: dict[str, float]

class JurySubmitRequest(BaseModel):
    username: str
    prediction_id: int
    is_correct: bool

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "model_version": "v1"}

@app.get("/leaderboard")
def leaderboard():
    db = SessionLocal()
    users = db.query(User).order_by(User.score.desc()).limit(10).all()
    db.close()
    return [{"username": u.username, "score": u.score, "trust_score": u.trust_score} for u in users]

@app.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    arr = np.array(req.pixels, dtype=np.uint8)[np.newaxis]
    result = classify_batch(arr)[0]
    
    db = SessionLocal()
    
    # 1. Vorhersage in der Datenbank speichern mega 
    db.add(Prediction(
        prediction=result["prediction"],
        confidence=result["confidence"],
        model_version="v1",
        is_honeypot=False
    ))
    
    # 2. Punkte berechnen und das Profil des Users aktualisieren
    points = 0
    if result["prediction"] == str(req.target_label):
        conf = result["confidence"]
        points = int(conf * 100) if conf <= 1.0 else int(conf)
        
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        user = User(username=req.username, score=0, trust_score=100)
        db.add(user)
        
    user.score += points
    db.commit()
    db.close()
    
    return result

@app.get("/jury/task")
def get_jury_task():
    db = SessionLocal()
    # holt mit einer Chance von 50 Prozent einen Honeypot zur Überprüfung
    if random.random() < 0.5:
        task = db.query(Prediction).filter(Prediction.is_honeypot == True).first()
    else:
        task = None
        
    if not task:
        task = db.query(Prediction).order_by(Prediction.created_at.desc()).limit(20).all()
        if task:
            task = random.choice(task)
            
    db.close()
    
    if not task:
        return {"error": "Keine Aufgaben vorhanden"}
        
    return {
        "prediction_id": task.id,
        "prediction": task.prediction,
        "is_honeypot": task.is_honeypot
    }

@app.post("/jury/submit")
def submit_jury_review(req: JurySubmitRequest):
    db = SessionLocal()
    
    task = db.query(Prediction).filter(Prediction.id == req.prediction_id).first()
    user = db.query(User).filter(User.username == req.username).first()
    
    if not user:
        user = User(username=req.username, score=0, trust_score=100)
        db.add(user)
        
    if task and task.is_honeypot:
        # Hier prüfe ob die Jury-Wertung mit dem echten Honeypot Label übereinstimmt
        actual_is_correct = (task.prediction == str(task.expected_label))
        if req.is_correct != actual_is_correct:
            user.trust_score = max(0, user.trust_score // 2)
            
    db.commit()
    db.close()
    return {"status": "success", "new_trust_score": user.trust_score}
