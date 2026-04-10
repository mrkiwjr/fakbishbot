import asyncio
import logging
import uuid

logger = logging.getLogger(__name__)

_scheduled: dict[str, dict] = {}


def schedule_broadcast(delay: float, coro_factory, text: str, schedule_at: str, media_type: str = None) -> str:
    task_id = str(uuid.uuid4())[:8]

    handle = asyncio.get_event_loop().call_later(
        delay,
        lambda tid=task_id: asyncio.ensure_future(_run(tid, coro_factory))
    )

    _scheduled[task_id] = {
        "handle": handle,
        "schedule_at": schedule_at,
        "text": text[:100],
        "media_type": media_type,
    }

    logger.info(f"Рассылка {task_id} запланирована на {schedule_at}")
    return task_id


async def _run(task_id: str, coro_factory):
    try:
        await coro_factory()
    finally:
        _scheduled.pop(task_id, None)


def cancel(task_id: str) -> bool:
    task = _scheduled.get(task_id)
    if not task:
        return False
    task["handle"].cancel()
    del _scheduled[task_id]
    logger.info(f"Рассылка {task_id} отменена")
    return True


def get_all() -> list[dict]:
    return [
        {"id": tid, "schedule_at": info["schedule_at"], "text": info["text"], "media_type": info.get("media_type")}
        for tid, info in _scheduled.items()
    ]
