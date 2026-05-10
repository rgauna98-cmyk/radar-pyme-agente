# agent/main.py — Servidor FastAPI + Webhook de WhatsApp

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial
from agent.providers import obtener_proveedor

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

PORT = int(os.getenv("PORT", 8000))
OWNER_PHONE = "+541137637100"

# Palabras clave que indican que alguien quiere una reunión o dejó datos
KEYWORDS_NOTIFICACION = [
    "el equipo se pondrá en contacto",
    "equipo se pondra en contacto",
    "coordinar esa reunión",
    "coordinar esa reunion",
    "agendar una reunión",
    "agendar una reunion",
    "nos pondremos en contacto",
]

proveedor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global proveedor
    await inicializar_db()
    proveedor = obtener_proveedor()
    logger.info("Base de datos inicializada")
    logger.info(f"Servidor AgentKit corriendo en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="AgentKit — Pablo (RADAR PYME)",
    version="1.0.0",
    lifespan=lifespan
)


def detectar_lead(respuesta: str) -> bool:
    """Detecta si Pablo está capturando un lead o solicitud de reunión."""
    respuesta_lower = respuesta.lower()
    return any(kw in respuesta_lower for kw in KEYWORDS_NOTIFICACION)


async def notificar_owner(telefono_cliente: str, mensaje_cliente: str):
    """Manda un WhatsApp al dueño del negocio cuando hay un lead."""
    notificacion = (
        f"*RADAR PYME — Nuevo Lead*\n\n"
        f"Un cliente quiere una reunion.\n"
        f"Telefono: {telefono_cliente}\n"
        f"Ultimo mensaje: {mensaje_cliente}\n\n"
        f"Contactalo a la brevedad."
    )
    await proveedor.enviar_mensaje(OWNER_PHONE, notificacion)
    logger.info(f"Notificacion enviada al owner por lead de {telefono_cliente}")


@app.get("/")
async def health_check():
    return {"status": "ok", "agente": "Pablo", "negocio": "RADAR PYME"}


@app.get("/debug")
async def debug_env():
    return {
        "ANTHROPIC_API_KEY": "SET" if os.getenv("ANTHROPIC_API_KEY") else "NOT SET",
        "WHATSAPP_PROVIDER": os.getenv("WHATSAPP_PROVIDER", "NOT SET"),
        "TWILIO_ACCOUNT_SID": "SET" if os.getenv("TWILIO_ACCOUNT_SID") else "NOT SET",
        "TWILIO_AUTH_TOKEN": "SET" if os.getenv("TWILIO_AUTH_TOKEN") else "NOT SET",
        "TWILIO_PHONE_NUMBER": os.getenv("TWILIO_PHONE_NUMBER", "NOT SET"),
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "NOT SET"),
    }


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        mensajes = await proveedor.parsear_webhook(request)

        for msg in mensajes:
            if msg.es_propio or not msg.texto:
                continue

            logger.info(f"Mensaje de {msg.telefono}: {msg.texto}")

            historial = await obtener_historial(msg.telefono)
            respuesta = await generar_respuesta(msg.texto, historial)

            await guardar_mensaje(msg.telefono, "user", msg.texto)
            await guardar_mensaje(msg.telefono, "assistant", respuesta)

            await proveedor.enviar_mensaje(msg.telefono, respuesta)

            # Notificar al dueño si Pablo detectó un lead
            if detectar_lead(respuesta) and msg.telefono != OWNER_PHONE:
                await notificar_owner(msg.telefono, msg.texto)

            logger.info(f"Respuesta a {msg.telefono}: {respuesta}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
