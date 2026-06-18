import asyncio
import logging
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from contextlib import asynccontextmanager
import sys

from config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка базы знаний из tenant-папки (tenants/test_clinic/)
KNOWLEDGE_BASE = ""
try:
    tenant_dir = Path(__file__).resolve().parent / "tenants" / "test_clinic"
    knowledge_path = tenant_dir / "knowledge.txt"

    if not tenant_dir.exists():
        logger.critical(f"Tenant directory not found: {tenant_dir}. Place tenant files in this folder.")
        print(f"❌ ERROR: Tenant directory not found: {tenant_dir}")
        sys.exit(1)

    if not knowledge_path.exists():
        logger.critical(f"Required file missing: {knowledge_path}")
        print(f"❌ ERROR: Required file missing: {knowledge_path}")
        sys.exit(1)

    with knowledge_path.open("r", encoding="utf-8") as f:
        KNOWLEDGE_BASE = f.read().strip()
    logger.info(f"Knowledge base loaded from {knowledge_path}")
except Exception as e:
    logger.error(f"Error reading knowledge.txt: {e}")
    print(f"❌ ERROR reading knowledge file: {e}")
    sys.exit(1)

# Снизим уровень логирования aiogram для меньшего шума
logging.getLogger("aiogram").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


async def create_bot():
    """
    Создать объект Bot с чистой асинхронной сессией (без прокси).
    На Linux-сервере прокси не требуется благодаря прямому доступу.
    """
    try:
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        logger.info("✅ Bot инициализирован успешно (без прокси)")
        return bot
    except Exception as e:
        logger.error(f"❌ Ошибка при создании bot: {e}")
        raise


# ============================================================================
# GLOBAL BOT & DISPATCHER (инициализируются в main())
# ============================================================================

bot = None
dp = None

from handlers import user_handlers

# Передаем базу знаний в модуль обработчиков
user_handlers.KNOWLEDGE_BASE = KNOWLEDGE_BASE


async def on_startup(dispatcher: Dispatcher):
    """Действия при запуске бота"""
    try:
        me = await bot.get_me()
        logger.info(f"✅ Bot started successfully")
        logger.info(f"   Bot username: @{me.username}")
        logger.info(f"   Bot name: {me.first_name}")
    except Exception as e:
        logger.error(f"❌ Failed to get bot info: {e}")


async def on_shutdown(dispatcher: Dispatcher):
    """Действия при остановке бота"""
    logger.info("Bot stopped")
    await bot.session.close()


@asynccontextmanager
async def lifespan(dispatcher: Dispatcher):
    """Контекстный менеджер для управления жизненным циклом"""
    await on_startup(dispatcher)
    yield
    await on_shutdown(dispatcher)


async def main():
    """Основная функция запуска бота"""
    global bot, dp

    # Инициализируем бота и диспетчер внутри main()
    bot = await create_bot()
    dp = Dispatcher(storage=MemoryStorage())

    from handlers import user_handlers

    # Очищаем внутреннее runtime state, чтобы не сохранять старые диалоги
    user_handlers.reset_runtime_state()

    # Передаем базу знаний в модуль обработчиков
    user_handlers.KNOWLEDGE_BASE = KNOWLEDGE_BASE

    # Подключение маршрутизатора
    dp.include_router(user_handlers.router)

    max_retries = 5
    retry_count = 0
    retry_delay = 5  # секунды
    
    while retry_count < max_retries:
        try:
            logger.info("Starting bot polling...")

            # Ensure no webhook is set (prevents conflicts when switching between
            # webhook and getUpdates) and give clear diagnostics if Telegram
            # reports a concurrent getUpdates client.
            try:
                await bot.delete_webhook(drop_pending_updates=True)
                logger.debug("Deleted existing webhook (if any)")
            except Exception as ex:
                logger.debug(f"Could not delete webhook (non-fatal): {ex}")

            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            # Если успешно начали polling, сбросим счетчик
            retry_count = 0
            retry_delay = 5
        except Exception as e:
            # Если сервер сообщает о конфликте getUpdates — чаще всего значит,
            # что уже запущен другой экземпляр бота. Выход с явным сообщением.
            msg = str(e)
            if "Conflict" in msg and "getUpdates" in msg:
                logger.critical(
                    "Telegram reports a getUpdates conflict. Make sure only one bot instance is running or remove other polling/webhook."
                )
                # Завершаем без дальнейших попыток — конфликт требует вмешательства.
                sys.exit(2)

            retry_count += 1
            logger.error(f"Error in main (attempt {retry_count}/{max_retries}): {e}")

            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                # Экспоненциальная задержка между попытками
                retry_delay = min(retry_delay * 2, 60)  # макс 60 секунд
            else:
                logger.critical("Max retries exceeded. Shutting down.")
                raise
        finally:
            try:
                await bot.session.close()
            except Exception as e:
                logger.warning(f"Error closing bot session: {e}")


if __name__ == "__main__":
    asyncio.run(main())
