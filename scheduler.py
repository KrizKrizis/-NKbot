# services/scheduler.py
# Планировщик задач: лотерея, проценты, доходы бизнесов, налоги, аукционы, менеджеры, выборы директора.

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def lottery_draw_job():
    """Ежечасная проверка и розыгрыш завершённых тиражей лотереи."""
    from lottery.handlers.lottery import process_finished_draws
    await process_finished_draws()


async def savings_interest_job():
    """Ежечасное начисление процентов по накопительным счетам."""
    from services.bank_service import apply_savings_interest_to_all
    await apply_savings_interest_to_all()


async def auction_incomes_job():
    """Каждые 3 часа: доход аукционных бизнесов."""
    from services.business_service import collect_all_auction_incomes
    await collect_all_auction_incomes()


async def personal_incomes_job():
    """Каждые 6 часов: доход личных бизнесов."""
    from services.business_service import collect_all_personal_incomes
    await collect_all_personal_incomes()


async def products_job():
    """Каждые 6 часов: списание стоимости продуктов."""
    from services.business_service import pay_all_products
    await pay_all_products()


async def taxes_job():
    """Каждые 12 часов: списание налогов."""
    from services.business_service import pay_all_taxes
    await pay_all_taxes()


async def auctions_check_job():
    """Каждую минуту: проверка и завершение аукционов."""
    from services.auction_service import check_and_finish_auctions
    await check_and_finish_auctions()


async def manager_salaries_job():
    """Каждые 6 часов: выплата зарплат менеджерам."""
    from services.business_service import process_all_manager_salaries
    await process_all_manager_salaries()


async def director_election_job():
    """Каждые 24 часа: проверка выборов директора и его смещение при плохой репутации."""
    from services.business_service import maybe_elect_director, remove_director_if_bad
    await maybe_elect_director()
    await remove_director_if_bad()


def init_scheduler():
    """Инициализирует и запускает планировщик со всеми задачами."""
    logger.info("Инициализация планировщика...")

    # Лотерея и проценты — каждый час в 00 минут
    scheduler.add_job(lottery_draw_job, 'cron', minute=0, id='lottery_draw', replace_existing=True)
    scheduler.add_job(savings_interest_job, 'cron', minute=0, id='savings_interest', replace_existing=True)

    # Доходы аукционных бизнесов — каждые 3 часа
    scheduler.add_job(auction_incomes_job, 'cron', hour='*/3', minute=0, id='auction_incomes', replace_existing=True)

    # Доходы личных бизнесов — каждые 6 часов
    scheduler.add_job(personal_incomes_job, 'cron', hour='*/6', minute=0, id='personal_incomes', replace_existing=True)

    # Продукты — каждые 6 часов
    scheduler.add_job(products_job, 'cron', hour='*/6', minute=0, id='products', replace_existing=True)

    # Налоги — каждые 12 часов
    scheduler.add_job(taxes_job, 'cron', hour='*/12', minute=0, id='taxes', replace_existing=True)

    # Проверка аукционов — каждую минуту
    scheduler.add_job(auctions_check_job, 'interval', minutes=1, id='auctions_check', replace_existing=True)

    # Зарплаты менеджерам — каждые 6 часов
    scheduler.add_job(manager_salaries_job, 'cron', hour='*/6', minute=0, id='manager_salaries', replace_existing=True)

    # Выборы директора — раз в сутки
    scheduler.add_job(director_election_job, 'interval', hours=24, id='director_election', replace_existing=True)

    scheduler.start()
    logger.info("Планировщик запущен.")