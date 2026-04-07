import logging
from aiohttp import web

from bot.api.routes import setup_routes, auth_middleware, cors_middleware

logger = logging.getLogger(__name__)

API_HOST = "0.0.0.0"
API_PORT = 8080


def create_api_app() -> web.Application:
    app = web.Application(
        middlewares=[cors_middleware, auth_middleware],
        client_max_size=10 * 1024 * 1024
    )
    setup_routes(app)
    return app


async def start_api_server(bot=None) -> web.AppRunner:
    app = create_api_app()

    if bot:
        app["bot"] = bot

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, API_HOST, API_PORT)
    await site.start()

    logger.info(f"API сервер запущен на {API_HOST}:{API_PORT}")
    return runner
