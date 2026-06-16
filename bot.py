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

# Безопасный импорт данных
from questions import QUIZ_DATA

try:
    from questions_prof import QUIZ_DATA_PROF
except ImportError:
    QUIZ_DATA_PROF = []

# Объединяем вопросы (если второй файл есть, бот его подхватит)
ALL_QUESTIONS = QUIZ_DATA + QUIZ_DATA_PROF

# Настройка логов
logging.basicConfig(level=logging.INFO)

TOKEN = "8842900248:AAEmooqY8nO8IxSC2RAMvpGy6ZbT4bRih_g"
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class QuizStates(StatesGroup):
    answering = State()

def get_options_keyboard(original_q_idx, options):
    keyboard = InlineKeyboardBuilder()
    for idx, option in enumerate(options):
        keyboard.button(text=option, callback_data=f"ans_{original_q_idx}_{idx}")
    keyboard.adjust(1)
    return keyboard.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await state.set_state(QuizStates.answering)
    
    question_indices = list(range(len(ALL_QUESTIONS)))
    random.shuffle(question_indices)
    
    await state.update_data(order=question_indices, current_step=0, score=0)
    
    first_original_idx = question_indices[0]
    first_q = ALL_QUESTIONS[first_original_idx]["question"]
    options = ALL_QUESTIONS[first_original_idx]["options"]
    
    await message.answer(
        f"📊 Начинаем тест по ЗУП 3.1!\n\n"
        f"**Вопрос 1 из {len(ALL_QUESTIONS)}:**\n{first_q}",
        parse_mode="Markdown",
        reply_markup=get_options_keyboard(first_original_idx, options)
    )

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

    correct_idx = ALL_QUESTIONS[q_idx]["correct_index"]
    if opt_idx == correct_idx:
        score += 1
        await callback_query.message.answer("✅ Правильно!")
    else:
        correct_text = ALL_QUESTIONS[q_idx]["options"][correct_idx]
        await callback_query.message.answer(f"❌ Неверно.\nПравильный ответ: {correct_text}")

    next_step = current_step + 1
    if next_step < len(order):
        await state.update_data(current_step=next_step, score=score)
        
        next_original_idx = order[next_step]
        next_q_text = ALL_QUESTIONS[next_original_idx]["question"]
        next_options = ALL_QUESTIONS[next_original_idx]["options"]
        
        await callback_query.message.answer(
            f"**Вопрос {next_step + 1} из {len(order)}:**\n{next_q_text}",
            parse_mode="Markdown",
            reply_markup=get_options_keyboard(next_original_idx, next_options)
        )
    else:
        await state.clear()
        await callback_query.message.answer(
            f"🏆 **Тест завершен!**\n\n"
            f"Результат: {score} из {len(order)}.\n\n"
            f"🔄 Нажмите /start для повтора."
        )
    
    # Безопасный ответ на колбэк
    try:
        await callback_query.answer()
    except Exception:
        pass

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