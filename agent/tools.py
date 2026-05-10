# agent/tools.py — Herramientas del agente RADAR PYME

import os
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")


def cargar_info_negocio() -> dict:
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    info = cargar_info_negocio()
    return {
        "horario": info.get("negocio", {}).get("horario", "24 horas, los 7 días de la semana"),
        "esta_abierto": True,
    }


def buscar_en_knowledge(consulta: str) -> str:
    """Busca información relevante en los archivos de /knowledge."""
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en mis archivos."


# ── FAQ ─────────────────────────────────────────────────────────────────────

def obtener_faqs() -> list[dict]:
    """Retorna las preguntas frecuentes de RADAR PYME."""
    return [
        {
            "pregunta": "¿Qué es RADAR PYME?",
            "respuesta": "RADAR PYME es una comunidad de negocios que conecta empresas PyMEs con el mundo corporativo. Brindamos asesoramiento en financiamiento, comercio exterior e importaciones, y organizamos eventos mensuales de capacitación y networking."
        },
        {
            "pregunta": "¿Qué servicios ofrecen?",
            "respuesta": "Ofrecemos: asesoramiento en financiamiento PyME, consultoría en comercio exterior e importaciones, eventos mensuales de capacitación, informes de coyuntura económica e internacional, y programas de sponsorship corporativo."
        },
        {
            "pregunta": "¿Cómo puedo participar en los eventos?",
            "respuesta": "Podés participar en nuestros seminarios mensuales de forma online (vía Zoom) o presencial en el Edificio Fortabat, Bouchard 610, piso 9, CABA. Los eventos comienzan a las 18hs. Contactanos para información sobre el próximo evento."
        },
        {
            "pregunta": "¿Dónde están ubicados?",
            "respuesta": "Nuestra sede está en el Edificio Fortabat, Bouchard 610, piso 9, Ciudad Autónoma de Buenos Aires. También realizamos eventos online vía Zoom."
        },
        {
            "pregunta": "¿Cómo puedo ser sponsor?",
            "respuesta": "Contamos con dos categorías de sponsorship: Bitcoin (máxima visibilidad) y Ether (visibilidad estándar). Cada una incluye diferentes beneficios de presencia de marca, acceso a la comunidad y participación en eventos. Agendá una reunión con nosotros para conocer los detalles."
        },
    ]


# ── AGENDADO DE REUNIONES ────────────────────────────────────────────────────

def registrar_solicitud_reunion(telefono: str, nombre: str, empresa: str, motivo: str) -> dict:
    """
    Registra una solicitud de reunión para seguimiento del equipo comercial.
    En producción, esto puede conectarse a un CRM o Google Calendar.
    """
    solicitud = {
        "telefono": telefono,
        "nombre": nombre,
        "empresa": empresa,
        "motivo": motivo,
        "fecha_solicitud": datetime.utcnow().isoformat(),
        "estado": "pendiente"
    }
    logger.info(f"Solicitud de reunión registrada: {solicitud}")
    return solicitud


# ── CALIFICACIÓN DE LEADS ────────────────────────────────────────────────────

def registrar_lead(telefono: str, nombre: str, empresa: str, cargo: str, email: str, interes: str) -> dict:
    """
    Registra un lead calificado para seguimiento comercial.
    En producción, esto puede conectarse a un CRM.
    """
    lead = {
        "telefono": telefono,
        "nombre": nombre,
        "empresa": empresa,
        "cargo": cargo,
        "email": email,
        "interes": interes,
        "fecha": datetime.utcnow().isoformat(),
        "estado": "nuevo"
    }
    logger.info(f"Lead registrado: {lead}")
    return lead


def clasificar_interes(mensaje: str) -> str:
    """Detecta el área de interés según el mensaje del potencial cliente."""
    mensaje_lower = mensaje.lower()
    if any(w in mensaje_lower for w in ["financiamiento", "crédito", "préstamo", "capital"]):
        return "financiamiento"
    elif any(w in mensaje_lower for w in ["importación", "importar", "comercio exterior", "aduana", "exportar"]):
        return "comercio_exterior"
    elif any(w in mensaje_lower for w in ["evento", "seminario", "capacitación", "networking"]):
        return "eventos"
    elif any(w in mensaje_lower for w in ["sponsor", "auspicio", "patrocinio", "marca"]):
        return "sponsorship"
    else:
        return "general"
