from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import Response, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from processing_logic import procesar_imagen_web

app = FastAPI()

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
    
    imagen_procesada_bytes = procesar_imagen_web(
        input_bytes, 
        redimensionar, 
        ancho, 
        alto, 
        anchor_bottom
    )
    
    return Response(content=imagen_procesada_bytes, media_type="image/png")

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")