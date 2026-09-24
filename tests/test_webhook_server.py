"""Tests pour le serveur de webhooks entrants."""

import pytest
from aiohttp import web

from api.webhook_server import handle_health


@pytest.mark.asyncio
async def test_webhook_health():
    app = web.Application()
    app.router.add_get("/health", handle_health)

    # Simulation requête GET /health
    req = None
    response = await handle_health(req)
    assert response.status == 200
    assert "ok" in response.text

