import os
import time
import logging
from collections import defaultdict
from functools import wraps
from aiohttp import web

from bot.api.auth import validate_init_data, check_admin, check_super_admin
from bot.config import ADMIN_ID, NOTIFICATION_CHAT_ID
from bot.services.database import db
from bot.services.promo import promo_service

logger = logging.getLogger(__name__)

_rate_limits: dict[str, list[float]] = defaultdict(list)
from bot.services.scheduler import schedule_broadcast as _schedule, cancel as _cancel_schedule, get_all as _get_scheduled
_broadcast_last: float = 0
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 10
BROADCAST_COOLDOWN = 120


def _check_rate_limit(key: str, max_requests: int = RATE_LIMIT_MAX) -> bool:
    now = time.time()
    _rate_limits[key] = [t for t in _rate_limits[key] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[key]) >= max_requests:
        return False
    _rate_limits[key].append(now)
    return True


def require_admin(handler):
    @wraps(handler)
    async def wrapper(request):
        user = request.get("user")
        if not user:
            return web.json_response({"error": "unauthorized"}, status=401)
        if not await check_admin(user["id"]):
            return web.json_response({"error": "forbidden"}, status=403)
        return await handler(request)
    return wrapper


def require_super_admin(handler):
    @wraps(handler)
    async def wrapper(request):
        user = request.get("user")
        if not user:
            return web.json_response({"error": "unauthorized"}, status=401)
        if not check_super_admin(user["id"]):
            return web.json_response({"error": "forbidden"}, status=403)
        return await handler(request)
    return wrapper


@web.middleware
async def auth_middleware(request, handler):
    if request.method == "OPTIONS":
        return await handler(request)

    if request.path == "/api/health":
        return await handler(request)

    init_data = request.headers.get("X-Telegram-Init-Data", "")

    if init_data == "dev" and os.getenv("DEV_MODE") == "1":
        remote = request.remote or ""
        if remote in ("127.0.0.1", "::1", "localhost"):
            request["user"] = {"id": ADMIN_ID, "first_name": "Dev"}
            return await handler(request)
        else:
            logger.warning(f"DEV_MODE запрос с внешнего IP: {remote}")
            return web.json_response({"error": "dev mode only from localhost"}, status=403)

    if not init_data:
        return web.json_response({"error": "missing init data"}, status=401)

    user = validate_init_data(init_data)
    if not user:
        return web.json_response({"error": "invalid init data"}, status=401)

    request["user"] = user
    return await handler(request)


@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        response = await handler(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Telegram-Init-Data"
    return response


async def health(request):
    return web.json_response({"status": "ok"})


@require_admin
async def check_admin_status(request):
    user = request["user"]
    is_super = check_super_admin(user["id"])
    return web.json_response({"is_admin": True, "is_super_admin": is_super})


@require_admin
async def get_stats(request):
    users_count = await db.get_users_count()
    promos = await promo_service.get_all_promos()
    active_promos = len([p for p in promos if p["active"]])
    unused_promos = await db.get_unused_active_promos()
    usage_history = await db.get_promo_usage_with_users()

    return web.json_response({
        "users_count": users_count,
        "total_promos": len(promos),
        "active_promos": active_promos,
        "unused_active_promos": len(unused_promos),
        "total_issued": len(usage_history),
    })


@require_admin
async def get_promos(request):
    promos = await promo_service.get_all_promos()
    return web.json_response({"promos": promos})


@require_admin
async def add_promo(request):
    data = await request.json()
    code = data.get("code", "").strip()
    days = data.get("days", 7)

    if not code:
        return web.json_response({"error": "empty code"}, status=400)

    if len(code) > 100:
        return web.json_response({"error": "code too long"}, status=400)

    try:
        days = int(days)
        if days < 1 or days > 365:
            return web.json_response({"error": "days must be 1-365"}, status=400)
    except (ValueError, TypeError):
        return web.json_response({"error": "invalid days"}, status=400)

    success = await promo_service.create_promo(code, days)
    if not success:
        return web.json_response({"error": "promo already exists"}, status=409)

    logger.info(f"[API] Промокод '{code}' создан на {days} дней")
    return web.json_response({"success": True})


@require_admin
async def delete_promo(request):
    code = request.match_info["code"]
    success = await promo_service.delete_promo(code)
    if not success:
        return web.json_response({"error": "not found"}, status=404)

    logger.info(f"[API] Промокод '{code}' удален")
    return web.json_response({"success": True})


@require_admin
async def get_promo_history(request):
    history = await db.get_promo_usage_with_users()
    return web.json_response({"history": history})


@require_admin
async def broadcast(request):
    global _broadcast_last
    now = time.time()
    if now - _broadcast_last < BROADCAST_COOLDOWN:
        remaining = int(BROADCAST_COOLDOWN - (now - _broadcast_last))
        return web.json_response({"error": f"cooldown {remaining}s"}, status=429)

    reader = await request.multipart()
    text = ""
    photo_bytes = None
    video_bytes = None
    schedule_at = ""

    while True:
        part = await reader.next()
        if part is None:
            break
        if part.name == "text":
            text = (await part.text()).strip()
        elif part.name == "photo":
            photo_bytes = await part.read()
            if len(photo_bytes) > 10 * 1024 * 1024:
                return web.json_response({"error": "photo too large (max 10MB)"}, status=400)
        elif part.name == "video":
            video_bytes = await part.read()
            if len(video_bytes) > 50 * 1024 * 1024:
                return web.json_response({"error": "video too large (max 50MB)"}, status=400)
        elif part.name == "schedule_at":
            schedule_at = (await part.text()).strip()

    if not text:
        return web.json_response({"error": "empty text"}, status=400)

    _broadcast_last = now

    from bot.services.broadcast import broadcast_service
    from io import BytesIO
    bot = request.app.get("bot")

    if not bot:
        return web.json_response({"error": "bot not available"}, status=500)

    if schedule_at:
        from datetime import datetime
        try:
            scheduled_time = datetime.strptime(schedule_at, "%Y-%m-%dT%H:%M")
        except ValueError:
            return web.json_response({"error": "invalid schedule format"}, status=400)

        now_dt = datetime.now()
        if scheduled_time <= now_dt:
            return web.json_response({"error": "schedule must be in the future"}, status=400)

        delay = (scheduled_time - now_dt).total_seconds()

        media_file_id = None
        media_type = None
        if photo_bytes:
            msg = await bot.send_photo(chat_id=ADMIN_ID, photo=BytesIO(photo_bytes), caption="[upload]")
            media_file_id = msg.photo[-1].file_id
            media_type = "photo"
            await msg.delete()
        elif video_bytes:
            msg = await bot.send_video(chat_id=ADMIN_ID, video=BytesIO(video_bytes), caption="[upload]", supports_streaming=True)
            media_file_id = msg.video.file_id
            media_type = "video"
            await msg.delete()

        b = bot
        t = text
        mfid = media_file_id
        mt = media_type

        async def execute():
            await _execute_scheduled_broadcast(b, t, mfid, mt)

        task_id = _schedule(delay, execute, text, schedule_at, media_type)

        logger.info(f"[API] Рассылка {task_id} запланирована на {schedule_at}")
        return web.json_response({"scheduled": True, "schedule_at": schedule_at, "task_id": task_id})

    photo_file_id = None
    video_file_id = None
    if photo_bytes:
        msg = await bot.send_photo(chat_id=ADMIN_ID, photo=BytesIO(photo_bytes), caption="[upload]")
        photo_file_id = msg.photo[-1].file_id
        await msg.delete()
    elif video_bytes:
        msg = await bot.send_video(chat_id=ADMIN_ID, video=BytesIO(video_bytes), caption="[upload]", supports_streaming=True)
        video_file_id = msg.video.file_id
        await msg.delete()

    result = await broadcast_service.send_broadcast(bot, text, photo_file_id, video_file_id)
    logger.info(f"[API] Рассылка: отправлено {result['sent']}, ошибок {result['failed']}")
    return web.json_response(result)


async def _execute_scheduled_broadcast(bot, text, media_file_id, media_type):
    from bot.services.broadcast import broadcast_service
    photo_id = media_file_id if media_type == "photo" else None
    video_id = media_file_id if media_type == "video" else None
    result = await broadcast_service.send_broadcast(bot, text, photo_id, video_id)
    logger.info(f"[API] Запланированная рассылка выполнена: отправлено {result['sent']}, ошибок {result['failed']}")


@require_admin
async def get_users(request):
    users = await db.get_all_users()
    return web.json_response({"users": users})


@require_super_admin
async def get_admins(request):
    admins = await db.get_all_admins()
    return web.json_response({
        "admins": admins,
        "super_admin_id": ADMIN_ID
    })


@require_super_admin
async def add_admin_user(request):
    data = await request.json()
    username = data.get("username", "").strip().lstrip("@").lower()

    if not username:
        return web.json_response({"error": "empty username"}, status=400)

    user = await db.get_user_by_username(username)
    if not user:
        return web.json_response({"error": "user not found"}, status=404)

    if user["user_id"] == ADMIN_ID:
        return web.json_response({"error": "already super admin"}, status=409)

    if await db.is_admin(user["user_id"]):
        return web.json_response({"error": "already admin"}, status=409)

    success = await db.add_admin(
        user["user_id"], user["first_name"], ADMIN_ID, user.get("username")
    )
    if not success:
        return web.json_response({"error": "failed to add"}, status=500)

    logger.info(f"[API] Добавлен админ: {user['first_name']} (ID: {user['user_id']})")
    return web.json_response({"success": True})


@require_super_admin
async def remove_admin_user(request):
    try:
        admin_id = int(request.match_info["user_id"])
    except ValueError:
        return web.json_response({"error": "invalid user_id"}, status=400)

    if admin_id == ADMIN_ID:
        return web.json_response({"error": "cannot remove super admin"}, status=400)

    success = await db.remove_admin(admin_id)
    if not success:
        return web.json_response({"error": "not found"}, status=404)

    logger.info(f"[API] Удален админ ID: {admin_id}")
    return web.json_response({"success": True})


def _escape_html(text: str) -> str:
    if not text:
        return ''
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


async def submit_booking(request):
    user = request["user"]
    rate_key = f"booking:{user['id']}"
    if not _check_rate_limit(rate_key, 5):
        return web.json_response({"error": "too many requests"}, status=429)

    data = await request.json()

    zone = data.get("zone", "").strip()[:50]
    duration = data.get("duration", "").strip()[:20]
    date = data.get("date", "").strip()[:20]
    time_val = data.get("time", "").strip()[:20]
    name = data.get("name", "").strip()[:100]
    phone = data.get("phone", "").strip()[:20]

    if not all([zone, duration, date, time_val, name, phone]):
        return web.json_response({"error": "all fields required"}, status=400)

    bot = request.app.get("bot")
    if not bot:
        return web.json_response({"error": "bot not available"}, status=500)

    msg = (
        f"🎯 <b>НОВАЯ БРОНЬ (Web App)</b>\n\n"
        f"<b>Клиент:</b>\n"
        f"👤 {_escape_html(name)}\n"
        f"📱 {_escape_html(phone)}\n\n"
        f"<b>Данные брони:</b>\n"
        f"🏷 Зона: {_escape_html(zone)}\n"
        f"⏱ Длительность: {_escape_html(duration)}\n"
        f"📅 Дата: {_escape_html(date)}\n"
        f"🕐 Время: {_escape_html(time_val)}\n"
    )

    try:
        await bot.send_message(chat_id=NOTIFICATION_CHAT_ID, text=msg, parse_mode="HTML")
        logger.info(f"[API] Бронь от {name}: {zone}, {duration}, {date} {time_val}")
        return web.json_response({"success": True})
    except Exception as e:
        logger.error(f"[API] Ошибка отправки брони: {e}")
        return web.json_response({"error": "send failed"}, status=500)


async def submit_feedback(request):
    user = request["user"]
    rate_key = f"feedback:{user['id']}"
    if not _check_rate_limit(rate_key, 3):
        return web.json_response({"error": "too many requests"}, status=429)

    data = await request.json()

    fio = data.get("fio", "").strip()[:100]
    comment = data.get("comment", "").strip()[:1000]

    if not fio or not comment:
        return web.json_response({"error": "fio and comment required"}, status=400)

    bot = request.app.get("bot")
    if not bot:
        return web.json_response({"error": "bot not available"}, status=500)

    msg = (
        f"💬 <b>НОВЫЙ ОТЗЫВ (Web App)</b>\n\n"
        f"<b>Пользователь:</b>\n"
        f"👤 {_escape_html(fio)}\n\n"
        f"<b>Текст отзыва:</b>\n"
        f"{_escape_html(comment)}\n"
    )

    try:
        await bot.send_message(chat_id=NOTIFICATION_CHAT_ID, text=msg, parse_mode="HTML")
        logger.info(f"[API] Отзыв от {fio}")
        return web.json_response({"success": True})
    except Exception as e:
        logger.error(f"[API] Ошибка отправки отзыва: {e}")
        return web.json_response({"error": "send failed"}, status=500)


@require_admin
async def get_scheduled_broadcasts(request):
    return web.json_response({"scheduled": _get_scheduled()})


@require_admin
async def cancel_scheduled_broadcast(request):
    task_id = request.match_info["task_id"]
    if not _cancel_schedule(task_id):
        return web.json_response({"error": "not found"}, status=404)
    return web.json_response({"success": True})


def setup_routes(app: web.Application):
    app.router.add_get("/api/health", health)
    app.router.add_get("/api/admin/check", check_admin_status)
    app.router.add_get("/api/admin/stats", get_stats)
    app.router.add_get("/api/admin/promos", get_promos)
    app.router.add_post("/api/admin/promos", add_promo)
    app.router.add_delete("/api/admin/promos/{code}", delete_promo)
    app.router.add_get("/api/admin/promo-history", get_promo_history)
    app.router.add_get("/api/admin/users", get_users)
    app.router.add_post("/api/admin/broadcast", broadcast)
    app.router.add_get("/api/admin/broadcast/scheduled", get_scheduled_broadcasts)
    app.router.add_delete("/api/admin/broadcast/scheduled/{task_id}", cancel_scheduled_broadcast)
    app.router.add_get("/api/admin/admins", get_admins)
    app.router.add_post("/api/admin/admins", add_admin_user)
    app.router.add_delete("/api/admin/admins/{user_id}", remove_admin_user)
    app.router.add_post("/api/booking", submit_booking)
    app.router.add_post("/api/feedback", submit_feedback)
