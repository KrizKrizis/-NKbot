# services/work_service.py
# Логика работы с работами: запуск, завершение, расчёт наград.

import random
import json
from datetime import datetime, timezone, timedelta
from db.database import db


async def get_job_info(job_id: str) -> dict:
    """Возвращает информацию о работе по её идентификатору."""
    return await db.fetchone("SELECT * FROM jobs WHERE job_id = ?", job_id)


async def get_job_settings(job_id: str) -> dict:
    """Возвращает настройки зарплаты для работы."""
    return await db.fetchone("SELECT reward_min, reward_max FROM work_settings WHERE job_id = ?", job_id)


async def get_job_bonuses(job_id: str) -> list:
    """Возвращает список бонусных предметов для работы."""
    return await db.fetchall("SELECT item_id, chance FROM work_bonuses WHERE job_id = ?", job_id)


async def start_work(user_id: int, job_id: str) -> None:
    """
    Запускает работу для игрока, генерирует награду и дропы.
    Предполагается, что все проверки (уровень, город, предметы, отсутствие другой работы)
    уже выполнены обработчиком.
    """
    job = await get_job_info(job_id)
    settings = await get_job_settings(job_id)
    if not settings:
        settings = {"reward_min": job["base_reward_min"], "reward_max": job["base_reward_max"]}

    # Генерируем зарплату
    reward = random.randint(settings["reward_min"], settings["reward_max"])

    # Генерируем дропы для начальных работ
    drop_data = {}
    bonuses = await get_job_bonuses(job_id)
    if bonuses:
        for bonus in bonuses:
            if random.random() < bonus["chance"]:
                if bonus["item_id"] == "4.1.15":  # Ящик с инструментами
                    qty = random.randint(2, 10)
                else:
                    qty = 1
                drop_data[bonus["item_id"]] = drop_data.get(bonus["item_id"], 0) + qty

    now = datetime.now(timezone.utc)
    end_time = now + timedelta(minutes=job["duration_minutes"])

    await db.execute(
        """
        UPDATE users
        SET current_work = ?,
            work_start_time = ?,
            work_end_time = ?,
            work_reward = ?,
            work_drop_data = ?
        WHERE vk_id = ?
        """,
        job_id, now.isoformat(), end_time.isoformat(), reward, json.dumps(drop_data), user_id
    )


async def finish_work(user_id: int) -> tuple:
    """
    Завершает текущую работу игрока, начисляет деньги и предметы.
    Не начисляет опыт и не повышает уровень.
    Возвращает (True, сообщение) при успехе.
    """
    user = await db.fetchone(
        "SELECT current_work, work_reward, work_drop_data FROM users WHERE vk_id = ?",
        user_id
    )
    if not user or not user["current_work"]:
        return False, "Нет активной работы."

    reward = user["work_reward"]
    drop_data_str = user["work_drop_data"]

    # Начисляем зарплату наличными
    await db.execute(
        "UPDATE users SET balance = balance + ? WHERE vk_id = ?",
        reward, user_id
    )

    # Начисляем предметы
    if drop_data_str:
        drop_data = json.loads(drop_data_str)
        for item_id, qty in drop_data.items():
            existing = await db.fetchone(
                "SELECT id, quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                user_id, item_id
            )
            if existing:
                await db.execute(
                    "UPDATE inventory SET quantity = quantity + ? WHERE id = ?",
                    qty, existing["id"]
                )
            else:
                await db.execute(
                    "INSERT INTO inventory (user_id, item_id, quantity) VALUES (?, ?, ?)",
                    user_id, item_id, qty
                )

    # Очищаем поля работы
    await db.execute(
        """
        UPDATE users
        SET current_work = NULL,
            work_start_time = NULL,
            work_end_time = NULL,
            work_reward = NULL,
            work_drop_data = NULL
        WHERE vk_id = ?
        """,
        user_id
    )

    parts = [f"Вы заработали {reward} NK"]
    if drop_data_str:
        drop_data = json.loads(drop_data_str)
        for item_id, qty in drop_data.items():
            item = await db.fetchone("SELECT name FROM items WHERE item_id = ?", item_id)
            if item:
                parts.append(f"{item['name']} x{qty}")
    message = "Работа завершена.\n" + "\n".join(parts)
    return True, message