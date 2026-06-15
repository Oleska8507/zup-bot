import asyncio
import logging
import os
import random  # <-- Добавили модуль для рандома
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
def get_options_keyboard(options):
    keyboard = InlineKeyboardBuilder()
    for idx, option in enumerate(options):
        keyboard.button(text=option, callback_data=f"ans_{idx}")
    keyboard.adjust(1)
    return keyboard.as_markup()

# Старт бота
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(QuizStates.answering)
    
    # Делаем копию списка вопросов и перемешиваем её случайным образом
    shuffled_questions = QUIZ_DATA.copy()
    random.shuffle(shuffled_questions)
    
    # Сохраняем перемешанный список вопросов и начальные очки в память пользователя (FSM)
    await state.update_data(questions=shuffled_questions, current_question=0, score=0)
    
    first_q = shuffled_questions[0]["question"]
    options = shuffled_questions[0]["options"]
    
    await message.answer(
        f"📊 Начинаем тест по формам 1С:ЗУП 3.1!\nВопросы будут идти в случайном порядке.\n\n"
        f"**Вопрос 1 из {len(shuffled_questions)}:**\n{first_q}",
        parse_mode="Markdown",
        reply_markup=get_options_keyboard(options)
    )

# Обработка ответов
@dp.callback_query(lambda c: c.data.startswith("ans_"))
async def handle_answer(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != QuizStates.answering:
        await callback_query.answer("Тест уже завершен. Нажмите /start для начала нового.")
        return

    # Получаем данные о текущем тесте из памяти
    user_data = await state.get_data()
    questions = user_data.get("questions", QUIZ_DATA)
    current_q_idx = user_data.get("current_question", 0)
    score = user_data.get("score", 0)
    
    # Извлекаем выбранный пользователем индекс ответа
    opt_idx = int(callback_query.data.split("_")[1])

    # Проверяем правильность ответа на основе перемешанного списка
    correct_idx = questions[current_q_idx]["correct_index"]
    if opt_idx == correct_idx:
        score += 1
        await callback_query.message.answer("✅ Правильно!")
    else:
        correct_text = questions[current_q_idx]["options"][correct_idx]
        await callback_query.message.answer(f"❌ Неверно.\nПравильный ответ: {correct_text}")

    # Переходим к следующему вопросу
    next_q_idx = current_q_idx + 1
    if next_q_idx < len(questions):
        await state.update_data(current_question=next_q_idx, score=score)
        
        next_q_text = questions[next_q_idx]["question"]
        next_options = questions[next_q_idx]["options"]
        
        await callback_query.message.answer(
            f"**Вопрос {next_q_idx + 1} из {len(questions)}:**\n{next_q_text}",
            parse_mode="Markdown",
            reply_markup=get_options_keyboard(next_options)
        )
    else:
        # --- ФИНАЛ ТЕСТА ---
        await state.clear()
        await callback_query.message.answer(
            f"🏆 **Тест успешно завершен!**\n\n"
            f"Ваш итоговый результат: {score} из {len(questions)} правильных ответов.\n\n"
            f"🔄 Если вы хотите пройти тест еще раз (вопросы снова перемешаются), просто нажмите /start"
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