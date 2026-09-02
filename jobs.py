# jobs/permanent/handlers/jobs.py
# Обработчики работ категории "Постоянные".

import logging
from datetime import datetime, timezone
from vkbottle.bot import Blueprint, Message
from db.database import db
from services.work_service import start_work, finish_work, get_job_info
from utils.formatting import format_duration
from jobs.permanent.keyboards.jobs import (
    get_permanent_jobs_keyboard,
    get_job_info_keyboard,
    get_active_work_keyboard,
)

logger = logging.getLogger(__name__)

bp = Blueprint("permanent_jobs")


async def get_available_permanent_jobs() -> list:
    """Возвращает список работ категории permanent."""
    return await db.fetchall("SELECT job_id, name FROM jobs WHERE category = 'permanent'")


async def show_permanent_jobs(message: Message):
    """Показывает список доступных постоянных работ."""
    user_id = message.from_id

    active = await db.fetchone("SELECT current_work FROM users WHERE vk_id = ?", user_id)
    if active and active["current_work"]:
        await show_active_work(message)
        return

    jobs = await get_available_permanent_jobs()
    if not jobs:
        await message.answer("Нет доступных работ этой категории.")
        return

    await message.answer("Постоянные работы:", keyboard=get_permanent_jobs_keyboard(jobs))


@bp.on.message(payload={"cmd": "permanent_job_info"})
async def permanent_job_info(message: Message):
    payload = message.get_payload_json()
    job_id = payload.get("job_id")
    job = await get_job_info(job_id)
    if not job:
        return

    duration_text = format_duration(job["duration_minutes"])
    text = f"{job['name']}\nДлительность: {duration_text}"

    await message.answer(text, keyboard=get_job_info_keyboard(job_id))


@bp.on.message(payload={"cmd": "start_work_permanent"})
async def start_work_permanent(message: Message):
    payload = message.get_payload_json()
    job_id = payload.get("job_id")

    success, msg = await start_work(message.from_id, job_id)
    if not success:
        await show_permanent_jobs(message)
        return

    await show_active_work(message)


async def show_active_work(message: Message):
    """Показывает экран с активной работой и таймером."""
    user = await db.fetchone(
        "SELECT current_work, work_start_time, work_end_time FROM users WHERE vk_id = ?",
        message.from_id
    )
    if not user or not user["current_work"]:
        return

    job_id = user["current_work"]
    job = await get_job_info(job_id)
    end_time = datetime.fromisoformat(user["work_end_time"])
    now = datetime.now(timezone.utc)
    remaining = end_time - now
    if remaining.total_seconds() < 0:
        success, msg = await finish_work(message.from_id)
        await message.answer(msg)
        await show_permanent_jobs(message)
        return

    total_seconds = int(remaining.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    time_left = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    duration_text = format_duration(job["duration_minutes"])
    text = f"Работа: {job['name']}\nОсталось: {time_left}\nДлительность: {duration_text}"

    await message.answer(text, keyboard=get_active_work_keyboard())


@bp.on.message(payload={"cmd": "refresh_work_permanent"})
async def refresh_work_permanent(message: Message):
    await show_active_work(message)


@bp.on.message(payload={"cmd": "cancel_work_permanent"})
async def cancel_work_permanent(message: Message):
    await db.execute(
        """
        UPDATE users
        SET current_work = NULL, work_start_time = NULL, work_end_time = NULL,
            work_reward = NULL, work_drop_data = NULL
        WHERE vk_id = ?
        """,
        message.from_id
    )
    await message.answer("Работа отменена.")
    await show_permanent_jobs(message)


@bp.on.message(payload={"cmd": "jobs_category_back"})
async def jobs_category_back(message: Message):
    payload = message.get_payload_json()
    category = payload.get("category")
    if category == "permanent":
        await show_permanent_jobs(message)
    else:
        from jobs.menu import show_categories
        await show_categories(message)