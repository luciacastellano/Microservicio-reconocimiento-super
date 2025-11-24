# Librerias estandar
import io
import os
from collections import Counter
from contextlib import asynccontextmanager

# Librerias de terceros
import requests
import gdown
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from ultralytics import YOLO
from PIL import Image




MODEL_PATH = "best.pt"
DRIVE_ID = "1XN7JJxfl4TKy7kp0QMM1NB3j0-zom01h"  # ID de Google Drive
MODEL_URL = f"https://drive.google.com/uc?id={DRIVE_ID}"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Código que se ejecuta al iniciar la app
    if not os.path.exists(MODEL_PATH):
        print("Descargando modelo desde Google Drive...")
        gdown.download(MODEL_URL, MODEL_PATH, quiet=False)
    
    # Cargar el modelo y guardarlo en app.state
    app.state.model = YOLO(MODEL_PATH)
    
    yield  # La app ya está lista para recibir requests
    
    # Código opcional al cerrar la app (shutdown)
    print("Microservicio cerrado.")

app = FastAPI(title="Microservicio YOLO", lifespan=lifespan)

@app.get("/")
def home():
    return {"message": "Microservicio YOLO funcionando correctamente"}

@app.post("/predict")
async def predict(image: UploadFile = File(...), conf_threshold: float = 0.25):
    """
    Recibe una imagen (campo 'image') y devuelve los productos detectados con su cantidad.
    """
    contents = await image.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Archivo inválido: {e}")

    # Convertir a numpy array
    img_arr = np.array(img)
    model = app.state.model
    # Inferencia
    results = model(img_arr, imgsz=640, conf=conf_threshold)
    r = results[0]

    detections = []
    boxes = getattr(r, "boxes", None)
    if boxes:
        try:
            cls_ids = boxes.cls.cpu().numpy()
        except Exception:
            cls_ids = getattr(boxes, "cls", [])

        for cls in cls_ids:
            label = model.names[int(cls)]
            detections.append(label)

    # Contar cuántas veces aparece cada producto
    conteo = Counter(detections)

    # Crear estructura en el formato esperado
    objects = [{"nombre": nombre, "cantidad": cantidad} for nombre, cantidad in conteo.items()]

    return JSONResponse(content={"objects": objects})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5000))
    uvicorn.run(app, host="0.0.0.0", port=port)