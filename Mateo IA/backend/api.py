"""
API REST de Mateo AI Ultra
=========================
API FastAPI para interactuar con Mateo desde el frontend.
"""

import json
import time
import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import shutil
import tempfile

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from main import get_mateo, MateoUltra
from tools import file_processor
from tools import voice as voice_tools
from utils.logger import setup_logger

logger = setup_logger("MateoAPI")

# ==========================================
# AUTENTICACIÓN OPCIONAL
# ==========================================
# Si se define MATEO_API_KEY en el .env, los endpoints que modifican estado o
# consumen recursos (chat, subida de archivos, voz, auto-mejora) exigen el
# header `X-API-Key`. Si NO se define, el comportamiento es el de siempre
# (pensado para uso 100% local en localhost) — no rompe instalaciones existentes.
def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    expected = os.getenv("MATEO_API_KEY", "").strip()
    if not expected:
        return  # Sin API key configurada: acceso libre (uso local)
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="X-API-Key inválida o faltante")


# Modelos de datos
class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=12000)
    user_id: str = Field(default="default", min_length=1, max_length=100)
    use_tools: bool = Field(default=True)


class MessageResponse(BaseModel):
    response: str
    query_type: str
    knowledge_used: bool
    tool_used: Optional[str] = None
    timestamp: str
    processing_time: float


class StatsResponse(BaseModel):
    total_messages: int
    api_calls: int
    knowledge_queries: int
    uptime_seconds: float
    vector_store_stats: Dict[str, Any]
    conversation_length: int


class ToolInfo(BaseModel):
    name: str
    description: str
    available: bool


# Instancia global
mateo: Optional[MateoUltra] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación."""
    global mateo
    
    logger.info("🚀 Iniciando Mateo AI Ultra API...")
    mateo = await get_mateo()
    logger.info("✅ API lista")
    
    yield
    
    logger.info("🛑 Cerrando API...")
    if mateo:
        await mateo.shutdown()


# Crear aplicación FastAPI
app = FastAPI(
    title="Mateo AI Ultra API",
    description="API para Mateo AI Ultra - Red Neuronal + Embeddings + APIs Externas",
    version="2.1.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "MATEO_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Endpoint raíz."""
    return {
        "name": "Mateo AI Ultra API",
        "version": "2.1.0",
        "status": "operational",
        "features": [
            "Modelo de lenguaje local (Ollama)",
            "Memoria vectorial ligera + bóveda Obsidian",
            "Wikipedia y búsqueda web (DuckDuckGo)",
            "Carga y generación de archivos (PDF, Word, Excel, Markdown)",
            "Voz: transcripción y síntesis local (opcional, ver /voice-status)"
        ],
        "docs": "/docs"
    }


@app.get("/ui", include_in_schema=False)
async def ui():
    """Sirve la interfaz oficial de Mateo desde el backend local."""
    path = Path(__file__).resolve().parent.parent / "frontend" / "UI NEW.HTML"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="La interfaz UI NEW.HTML no está instalada")
    return FileResponse(path, media_type="text/html")


@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest, _: None = Depends(require_api_key)):
    """
    Envía un mensaje a Mateo y recibe una respuesta inteligente.
    
    Args:
        request: Mensaje del usuario
        
    Returns:
        Respuesta de Mateo con metadatos
    """
    if not mateo or not mateo.core:
        raise HTTPException(status_code=503, detail="Mateo no está disponible")
    
    start = time.time()
    
    try:
        result = await mateo.core.process_message(
            message=request.message,
            user_id=request.user_id,
            use_tools=request.use_tools
        )
        
        processing_time = time.time() - start
        
        return MessageResponse(
            response=result["response"],
            query_type=result["query_type"],
            knowledge_used=result["rag_context_used"],
            tool_used=result["tool_used"],
            timestamp=datetime.now().isoformat(),
            processing_time=processing_time
        )
        
    except (KeyError, TypeError, ValueError) as e:
        logger.exception("Respuesta inválida del núcleo")
        raise HTTPException(status_code=502, detail="Respuesta inválida del núcleo") from e
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        raise HTTPException(status_code=500, detail="Error interno procesando el mensaje") from e


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Obtiene estadísticas del sistema.
    
    Returns:
        Estadísticas de uso
    """
    if not mateo:
        raise HTTPException(status_code=503, detail="Mateo no está disponible")
    
    stats = mateo.get_stats()
    return StatsResponse(**stats)


@app.get("/tools")
async def get_tools() -> List[ToolInfo]:
    """
    Obtiene lista de herramientas disponibles.
    
    Returns:
        Lista de herramientas
    """
    tools = []
    if mateo and mateo.core and mateo.core.external_apis:
        tools = mateo.core.external_apis.get_available_tools()
    return [ToolInfo(**tool) for tool in tools]



@app.post("/learn")
async def learn_text(text: str, source: str = "user", _: None = Depends(require_api_key)):
    """
    Enseña a Mateo un nuevo texto.
    
    Args:
        text: Texto a aprender
        source: Fuente del texto
        
    Returns:
        Confirmación
    """
    if not mateo:
        raise HTTPException(status_code=503, detail="Mateo no está disponible")
    
    await mateo.learn(text, source)
    
    return {
        "success": True,
        "message": f"Texto aprendido de {source}",
        "text_length": len(text)
    }


class AgentRunRequest(BaseModel):
    goal: str = Field(..., min_length=3, max_length=2000)
    max_steps: int = Field(default=8, ge=1, le=8)
    save_to_obsidian: bool = Field(default=False)


@app.post("/agent/run")
async def agent_run(request: AgentRunRequest, _: None = Depends(require_api_key)):
    """Ejecuta el Modo Agente de punta a punta sobre un objetivo y devuelve
    el desglose completo de pasos (tarea, herramienta usada, resultado) más
    el informe final. Pensado para uso programático/UI; para uso conversacional
    normal alcanza con escribir `/agente [objetivo]` en /chat."""
    if not mateo or not mateo.core or not mateo.core.agent_engine:
        raise HTTPException(status_code=503, detail="El motor de agente autónomo no está disponible")

    result = await mateo.core.agent_engine.run(
        request.goal,
        max_steps=request.max_steps,
        save_to_obsidian=request.save_to_obsidian,
    )
    return result


@app.post("/clear")
async def clear_history(user_id: str = "default", _: None = Depends(require_api_key)):
    """Limpia el historial de conversación del usuario indicado."""
    if not mateo or not mateo.core:
        raise HTTPException(status_code=503, detail="Mateo no está disponible")

    if not user_id.strip() or len(user_id) > 100:
        raise HTTPException(status_code=422, detail="user_id inválido")

    mateo.core.clear_history(user_id)
    
    return {
        "success": True,
        "message": "Historial limpiado"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    if mateo and mateo.running:
        provider = None
        model = None
        ollama_enabled = False
        try:
            provider = (mateo.config or {}).get("provider")
        except Exception:
            provider = None
        try:
            lm = getattr(getattr(mateo, "core", None), "language_model", None)
            if lm is not None:
                ollama_enabled = bool(getattr(lm, "use_ollama", False))
                if ollama_enabled:
                    provider = "ollama"
                    model = getattr(lm, "ollama_model", None)
                else:
                    model = getattr(lm, "model_name", None)
        except Exception:
            pass
        return {
            "status": "healthy",
            "mateo": "running",
            "provider": provider,
            "model": model,
            "ollama_enabled": ollama_enabled,
            "timestamp": datetime.now().isoformat()
        }
    return {
        "status": "unhealthy",
        "mateo": "not running"
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), _: None = Depends(require_api_key)):
    """Sube un archivo (PDF/Word/Excel/CSV/texto), extrae su texto y lo agrega
    a la memoria vectorial de Mateo para que pueda usarlo como contexto."""
    if not mateo or not mateo.core:
        raise HTTPException(status_code=503, detail="Mateo no está disponible")

    suffix = Path(file.filename or "").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        extracted = file_processor.load_file(tmp_path, original_name=file.filename)
    except file_processor.FileProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if mateo.core.vector_store and extracted["text"]:
        mateo.core.vector_store.add_texts(
            [extracted["text"]], metadatas=[{"source": extracted["name"], "kind": extracted["kind"]}]
        )

    preview = extracted["text"][:500]
    return {
        "success": True,
        "name": extracted["name"],
        "kind": extracted["kind"],
        "chars_extracted": len(extracted["text"]),
        "truncated": extracted["truncated"],
        "preview": preview,
        "added_to_memory": bool(mateo.core.vector_store),
    }


@app.post("/generate-file")
async def generate_file(
    title: str,
    content: str,
    format: str = "md",
    _: None = Depends(require_api_key),
):
    """Genera un archivo (docx/pdf/xlsx/md/txt) a partir de un título y contenido
    ya redactado, y devuelve la ruta para descargarlo con GET /files/{nombre}."""
    try:
        path = file_processor.generate_document(format, title, content)
    except file_processor.FileProcessingError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"success": True, "filename": path.name, "download_url": f"/files/{path.name}"}


@app.get("/files/{filename}")
async def download_file(filename: str, _: None = Depends(require_api_key)):
    """Descarga un archivo generado (documento o audio). Solo sirve nombres de
    archivo simples (sin rutas) desde las carpetas controladas por Mateo."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")

    for directory in (file_processor.GENERATED_DIR, voice_tools.AUDIO_DIR):
        candidate = directory / filename
        if candidate.is_file():
            return FileResponse(candidate)
    raise HTTPException(status_code=404, detail="Archivo no encontrado")


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...), _: None = Depends(require_api_key)):
    """Transcribe un audio (wav/mp3/webm/ogg) a texto usando faster-whisper (local)."""
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        result = voice_tools.transcribe_audio(tmp_path)
    except voice_tools.VoiceError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return result


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


@app.post("/speak")
async def speak(request: SpeakRequest, _: None = Depends(require_api_key)):
    """Sintetiza texto a voz (Piper, local) y devuelve un WAV para reproducir."""
    try:
        path = voice_tools.synthesize_speech(request.text)
    except voice_tools.VoiceError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    return FileResponse(path, media_type="audio/wav")


@app.get("/voice-status")
async def voice_status():
    """Indica si la transcripción (STT) y la síntesis (TTS) están realmente
    disponibles en este entorno, sin cargar los modelos pesados."""
    return voice_tools.voice_status()


# WebSocket para chat en tiempo real
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para chat en tiempo real."""
    expected_api_key = os.getenv("MATEO_API_KEY", "").strip()
    provided_api_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
    if expected_api_key and provided_api_key != expected_api_key:
        await websocket.close(code=1008, reason="X-API-Key inválida o faltante")
        return

    await manager.connect(websocket)
    
    try:
        while True:
            # Recibir mensaje
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "JSON inválido"})
                continue

            message = message_data.get("message", "")
            user_id = message_data.get("user_id", "default")
            if not isinstance(message, str) or not message.strip() or len(message) > 12000:
                await websocket.send_json({
                    "type": "error",
                    "content": "El mensaje debe tener entre 1 y 12000 caracteres"
                })
                continue
            if not isinstance(user_id, str) or not user_id.strip() or len(user_id) > 100:
                await websocket.send_json({"type": "error", "content": "user_id inválido"})
                continue
            
            # Procesar mensaje
            if mateo and mateo.core:
                result = await mateo.core.process_message(message, user_id)
                
                # Enviar respuesta
                response = {
                    "type": "response",
                    "content": result["response"],
                    "query_type": result["query_type"],
                    "tool_used": result["tool_used"],
                    "timestamp": datetime.now().isoformat()
                }
                
                await websocket.send_json(response)
            else:
                await websocket.send_json({
                    "type": "error",
                    "content": "Mateo no está disponible"
                })
                
    except WebSocketDisconnect:
        if websocket in manager.active_connections:
            manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        if websocket in manager.active_connections:
            manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
