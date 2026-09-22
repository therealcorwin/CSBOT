"""Serveur HTTP asynchrone (aiohttp) pour recevoir les alertes poussées par n8n et CPTCOPRO."""

from aiogram import Bot
from aiohttp import web
from loguru import logger
from config.settings import settings


async def handle_health(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "csbot"})


async def handle_n8n_alert(request: web.Request) -> web.Response:
    """Reçoit une alerte ou un message poussé depuis un scénario n8n."""
    bot: Bot = request.app["bot"]

    # Vérification du secret
    if settings.N8N_WEBHOOK_SECRET:
        auth_header = request.headers.get("X-Webhook-Secret") or request.query.get("secret")
        if auth_header != settings.N8N_WEBHOOK_SECRET:
            return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    title = data.get("title", "Alerte n8n")
    message = data.get("message", "")
    target = data.get("target", "cs")  # "cs" ou "copro"

    chat_id = settings.CS_GROUP_ID if target == "cs" else settings.COPRO_CHAT_ID

    if chat_id != 0 and message:
        formatted = f"🔔 <b>{title}</b>\n\n{message}"
        try:
            await bot.send_message(chat_id=chat_id, text=formatted, parse_mode="HTML")
            return web.json_response({"status": "delivered", "chat_id": chat_id})
        except Exception as e:
            logger.error(f"Erreur envoi message bot depuis webhook n8n : {e}")
            return web.json_response({"error": str(e)}, status=500)

    return web.json_response({"status": "ignored", "reason": "No target or empty message"})


async def handle_cptcopro_anomaly(request: web.Request) -> web.Response:
    """Reçoit une notification de détection d'anomalie financière depuis CPTCOPRO."""
    bot: Bot = request.app["bot"]
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    anom_type = data.get("type", "Anomalie financière")
    details = data.get("details", "")

    if settings.CS_GROUP_ID != 0:
        alert_msg = (
            "🚨 <b>ALERTE CPTCOPRO - DÉTECTION ANOMALIE FINANCIÈRE</b> 🚨\n\n"
            f"• <b>Type :</b> {anom_type}\n"
            f"• <b>Détails :</b>\n{details}\n\n"
            "<i>Consultez l'application Streamlit de CPTCOPRO pour les actions de recouvrement.</i>"
        )
        try:
            await bot.send_message(chat_id=settings.CS_GROUP_ID, text=alert_msg, parse_mode="HTML")
            return web.json_response({"status": "delivered"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    return web.json_response({"status": "ignored"})


async def start_webhook_server(bot: Bot) -> web.AppRunner:
    """Démarre le serveur HTTP léger pour écouter les webhooks entrants."""
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/health", handle_health)
    app.router.add_post("/webhook/n8n/alert", handle_n8n_alert)
    app.router.add_post("/webhook/cptcopro/anomaly", handle_cptcopro_anomaly)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.WEBHOOK_SERVER_HOST, port=settings.WEBHOOK_SERVER_PORT)
    await site.start()
    logger.info(f"Serveur Webhook d'écoute actif sur http://{settings.WEBHOOK_SERVER_HOST}:{settings.WEBHOOK_SERVER_PORT}")
    return runner

