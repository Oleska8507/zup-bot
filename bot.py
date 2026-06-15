import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from questions import register_handlers

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Инициализация бота (замените ТОКЕН на ваш настоящий)
TOKEN = "8842900248:AAEmooqY8nO8IxSC2RAMvpGy6ZbT4bRih_g"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Регистрируем обработчики из questions.py
register_handlers(dp)

# Крошечный веб-сервер для обмана Render.com
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render автоматически передает нужный порт в переменную окружения PORT
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    # Запускаем веб-сервер для Render
    await start_web_server()
    
    # Удаляем вебхуки, если они были, и запускаем опрос (Polling)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())