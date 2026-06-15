import asyncio
import logging
import os
import random
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

# Генерация кнопок
def get_options_keyboard(original_q_idx, options):
    keyboard = InlineKeyboardBuilder()
    for idx, option in enumerate(options):
        keyboard.button(text=option, callback_data=f"ans_{original_q_idx}_{idx}")
    keyboard.adjust(1)
    return keyboard.as_markup()

# Старт бота
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(QuizStates.answering)
    
    # Создаем список из индексов всех вопросов и перемешиваем его
    question_indices = list(range(len(QUIZ_DATA)))
    random.shuffle(question_indices)
    
    # Сохраняем последовательность в память
    await state.update_data(order=question_indices, current_step=0, score=0)
    
    first_original_idx = question_indices[0]
    first_q = QUIZ_DATA[first_original_idx]["question"]
    options = QUIZ_DATA[first_original_idx]["options"]
    
    # Убрали фразу про случайный порядок из текста подписи
    await message.answer(
        f"📊 Начинаем тест по формам 1С:ЗУП 3.1!\n\n"
        f"**Вопрос 1 из {len(QUIZ_DATA)}:**\n{first_q}",
        parse_mode="Markdown",
        reply_markup=get_options_keyboard(first_original_idx, options)
    )

# Обработка ответов
@dp.callback_query(lambda c: c.data.startswith("ans_"))
async def handle_answer(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != QuizStates.answering:
        await callback_query.answer("Тест уже завершен. Нажмите /start для начала нового.")
        return

    user_data = await state.get_data()
    order = user_data.get("order")
    current_step = user_data.get("current_step", 0)
    score = user_data.get("score", 0)
    
    _, q_idx, opt_idx = callback_query.data.split("_")
    q_idx, opt_idx = int(q_idx), int(opt_idx)
    
    if order[current_step] != q_idx:
        await callback_query.answer()
        return

    correct_idx = QUIZ_DATA[q_idx]["correct_index"]
    if opt_idx == correct_idx:
        score += 1
        await callback_query.message.answer("✅ Правильно!")
    else:
        correct_text = QUIZ_DATA[q_idx]["options"][correct_idx]
        await callback_query.message.answer(f"❌ Неверно.\nПравильный ответ: {correct_text}")

    next_step = current_step + 1
    if next_step < len(order):
        await state.update_data(current_step=next_step, score=score)
        
        next_original_idx = order[next_step]
        next_q_text = QUIZ_DATA[next_original_idx]["question"]
        next_options = QUIZ_DATA[next_original_idx]["options"]
        
        await callback_query.message.answer(
            f"**Вопрос {next_step + 1} из {len(order)}:**\n{next_q_text}",
            parse_mode="Markdown",
            reply_markup=get_options_keyboard(next_original_idx, next_options)
        )
    else:
        await state.clear()
        await callback_query.message.answer(
            f"🏆 **Тест успешно завершен!**\n\n"
            f"Ваш итоговый результат: {score} из {len(order)} правильных ответов.\n\n"
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