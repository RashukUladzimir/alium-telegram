import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import token

from handlers.user_actions import register_handlers_user

logger = logging.getLogger(__name__)

async def main():

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logger.error("Starting bot")

    bot = Bot(token=token)
    dp = Dispatcher(bot, storage=MemoryStorage())

    register_handlers_user(dp)

    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
