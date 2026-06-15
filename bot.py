# bot.py
import asyncio
import random
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiohttp import web  # Для обхода ограничений бесплатного хостинга

# Импортируем наши вопросы из questions.py
from questions import QUIZ_DATA

# ТОКЕН БОТА (вставьте ваш токен из BotFather)
BOT_TOKEN = "8842900248:AAEmooqY8nO8IxSC2RAMvpGy6ZbT4bRih_g" # Ваш токен

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class QuizStates(StatesGroup):
    in_progress = State()

class QuizCallback(CallbackData, prefix="quiz"):
    q_index: int
    o_index: int

def get_quiz_keyboard(q_index: int, selected_index: int = None):
    builder = InlineKeyboardBuilder()
    question = QUIZ_DATA[q_index]
    for idx, option in enumerate(question["options"]):
        text = option
        if selected_index is not None:
            if idx == question["correct_index"]:
                text = f"🟢 {option}"
            elif idx == selected_index:
                text = f"🔴 {option}"
        builder.button(text=text, callback_data=QuizCallback(q_index=q_index, o_index=idx).pack())
    if selected_index is not None:
        builder.button(text="Дальше ➡️", callback_data="next_question")
    builder.adjust(1)
    return builder.as_markup()

@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    user_data = await state.get_data()
    if current_state == QuizStates.in_progress and "order" in user_data:
        current_step = user_data.get("current_step", 0)
        order = user_data["order"]
        q_index = order[current_step]
        total = len(QUIZ_DATA)
        await message.answer(
            f"Вы остановились на вопросе **{current_step + 1} из {total}**. Продолжаем!\n\n"
            f"**Вопрос {current_step + 1}/{total}:**\n{QUIZ_DATA[q_index]['question']}",
            reply_markup=get_quiz_keyboard(q_index),
            parse_mode="Markdown"
        )
        return

    await state.clear()
    await state.set_state(QuizStates.in_progress)
    total = len(QUIZ_DATA)
    question_order = list(range(total))
    random.shuffle(question_order)
    await state.update_data(score=0, current_step=0, order=question_order)
    first_q_index = question_order[0]
    await message.answer(
        f"Привет! Добро пожаловать на случайное тестирование по формам ЗУП. Всего вопросов: {total}.\n\n"
        f"**Вопрос 1/{total}:**\n{QUIZ_DATA[first_q_index]['question']}",
        reply_markup=get_quiz_keyboard(first_q_index),
        parse_mode="Markdown"
    )

@dp.callback_query(QuizCallback.filter(), QuizStates.in_progress)
async def handle_answer(callback: types.CallbackQuery, callback_data: QuizCallback, state: FSMContext):
    q_index = callback_data.q_index
    o_index = callback_data.o_index
    correct_idx = QUIZ_DATA[q_index]["correct_index"]
    await callback.answer()
    user_data = await state.get_data()
    current_step = user_data.get("current_step", 0)
    order = user_data.get("order", [])
    if not order or order[current_step] != q_index:
        return

    is_correct = (o_index == correct_idx)
    current_score = user_data.get("score", 0)
    if is_correct:
        await state.update_data(score=current_score + 1)
        response_text = "✨ **Правильно!**"
    else:
        correct_text = QUIZ_DATA[q_index]["options"][correct_idx]
        response_text = f"❌ **Неверно.** Правильный ответ: *{correct_text}*"

    total = len(QUIZ_DATA)
    builder = InlineKeyboardBuilder()
    for idx, option in enumerate(QUIZ_DATA[q_index]["options"]):
        text = option
        if idx == correct_idx:
            text = f"🟢 {option}"
        elif idx == o_index:
            text = f"🔴 {option}"
        builder.button(text=text, callback_data=QuizCallback(q_index=q_index, o_index=idx).pack())
    if current_step + 1 < total:
        builder.button(text="Дальше ➡️", callback_data="next_question")
    else:
        builder.button(text="Показать результаты 🏁", callback_data="finish_quiz")
    builder.adjust(1)

    await callback.message.edit_text(
        text=f"**Вопрос {current_step + 1}/{total}:**\n{QUIZ_DATA[q_index]['question']}\n\n{response_text}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "next_question", QuizStates.in_progress)
async def next_question(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_data = await state.get_data()
    next_step = user_data.get("current_step", 0) + 1
    order = user_data.get("order", [])
    await state.update_data(current_step=next_step)
    next_q_index = order[next_step]
    total = len(QUIZ_DATA)
    await callback.message.edit_text(
        text=f"**Вопрос {next_step + 1}/{total}:**\n{QUIZ_DATA[next_q_index]['question']}",
        reply_markup=get_quiz_keyboard(next_q_index),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "finish_quiz", QuizStates.in_progress)
async def finish_quiz(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_data = await state.get_data()
    score = user_data.get("score", 0)
    total = len(QUIZ_DATA)
    await callback.message.edit_text(
        text=f"🎉 **Тестирование завершено!**\n\nТвой результат: **{score} из {total}** правильных ответов."
    )
    await state.clear()

# Хэндлер для веб-сервера (чтобы Render видел, что приложение «живо»)
async def handle_web(request):
    return web.Response(text="Bot is running!")

async def main():
    # Запуск веб-сервера параллельно с ботом
    app = web.Application()
    app.router.add_get("/", handle_web)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    asyncio.create_task(site.start())
    
    # Запуск самого бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())