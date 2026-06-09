from fastapi import FastAPI
from pydantic import BaseModel
import numpy as np
from app.classifier import classify_batch

# Pydantic-Modell für die Validierung der eingehenden Daten (28x28 Pixel-Array)
class ClassifyRequest(BaseModel):
    pixels: list[list[int]]

# Pydantic-Modell für die Validierung der ausgehenden Daten (API-Antwort)
class ClassifyResponse(BaseModel):
    prediction: str
    confidence: float
    scores: dict[str, float]

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "model_version": "v1"}

@app.get("/results")
def results():
    return {"results": [], "note": "persistence not yet implemented"}

@app.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    # Konvertiert die JSON-Liste in ein NumPy-Array mit der Form (1, 28, 28)
    arr = np.array(req.pixels, dtype=np.uint8)[np.newaxis]
    return classify_batch(arr)[0]
