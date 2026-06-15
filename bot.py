import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# Импортируем список вопросов из вашего файла questions.py
from questions import QUIZ_DATA

# Настройка логов
logging.basicConfig(level=logging.INFO)

# Инициализация бота
TOKEN = "8842900248:AAEmooqY8nO8IxSC2RAMvpGy6ZbT4bRih_g"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния для викторины
class QuizStates(StatesGroup):
    answering = State()

# Генерация кнопок с вариантами ответов
def get_options_keyboard(question_index):
    keyboard = InlineKeyboardBuilder()
    options = QUIZ_DATA[question_index]["options"]
    for idx, option in enumerate(options):
        keyboard.button(text=option, callback_data=f"ans_{question_index}_{idx}")
    keyboard.adjust(1)
    return keyboard.as_markup()

# Старт бота
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(QuizStates.answering)
    await state.update_data(current_question=0, score=0)
    
    first_q = QUIZ_DATA[0]["question"]
    await message.answer(
        f"📊 Начинаем тест по формам 1С:ЗУП 3.1!\n\n"
        f"**Вопрос 1 из {len(QUIZ_DATA)}:**\n{first_q}",
        parse_mode="Markdown",
        reply_markup=get_options_keyboard(0)
    )

# Обработка ответов
@dp.callback_query(lambda c: c.data.startswith("ans_"))
async def handle_answer(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != QuizStates.answering:
        await callback_query.answer("Тест уже завершен. Нажмите /start для начала нового.")
        return

    _, q_idx, opt_idx = callback_query.data.split("_")
    q_idx, opt_idx = int(q_idx), int(opt_idx)
    
    user_data = await state.get_data()
    current_q = user_data.get("current_question", 0)
    score = user_data.get("score", 0)
    
    if q_idx != current_q:
        await callback_query.answer()
        return

    correct_idx = QUIZ_DATA[current_q]["correct_index"]
    if opt_idx == correct_idx:
        score += 1
        await callback_query.message.answer("✅ Правильно!")
    else:
        correct_text = QUIZ_DATA[current_q]["options"][correct_idx]
        await callback_query.message.answer(f"❌ Неверно.\nПравильный ответ: {correct_text}")

    next_q = current_q + 1
    if next_q < len(QUIZ_DATA):
        await state.update_data(current_question=next_q, score=score)
        next_q_text = QUIZ_DATA[next_q]["question"]
        await callback_query.message.answer(
            f"**Вопрос {next_q + 1} из {len(QUIZ_DATA)}:**\n{next_q_text}",
            parse_mode="Markdown",
            reply_markup=get_options_keyboard(next_q)
        )
    else:
        # --- НАША ФИНАЛЬНАЯ ФРАЗА ТЕПЕРЬ ТУТ ---
        await state.clear()
        await callback_query.message.answer(
            f"🏆 **Тест успешно завершен!**\n\n"
            f"Ваш итоговый результат: {score} из {len(QUIZ_DATA)} правильных ответов.\n\n"
            f"🔄 Если вы хотите пройти тест еще раз, просто нажмите /start"
        )
    
    await callback_query.answer()

# Веб-сервер для Render
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await start_web_server()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())