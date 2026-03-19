import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
# Importamos new_session para el modelo liviano
from rembg import new_session 
from processing_logic import procesar_imagen_web

# CONFIGURACIÓN DE ENTORNO PARA RENDER
# Esto le dice a la IA que use una carpeta local para el modelo y no explote por permisos
os.environ["U2NET_HOME"] = os.path.join(os.getcwd(), ".u2net")

app = FastAPI()

# Creamos la sesión UNA SOLA VEZ al iniciar (modelo ultra liviano de 4MB)
# Al estar en el scope global, se carga cuando el servidor hace "startup"
session_ia = new_session("u2netp")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/remove-bg")
async def remove_background_endpoint(
    file: UploadFile = File(...),
    redimensionar: bool = Form(False),
    ancho: int = Form(512),
    alto: int = Form(512),
    anchor_bottom: bool = Form(False)
):
    input_bytes = await file.read()
    
    # Pasamos la session_ia a tu lógica de procesamiento
    imagen_procesada_bytes = procesar_imagen_web(
        input_bytes, 
        redimensionar, 
        ancho, 
        alto, 
        anchor_bottom,
        session=session_ia  # <--- IMPORTANTE: Pasalo acá
    )
    
    return Response(content=imagen_procesada_bytes, media_type="image/png")

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")