import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter

# Токен берётся ТОЛЬКО из переменной окружения. Никаких хардкодов в коде —
# если токен утечёт вместе с кодом (например, в публичный репозиторий),
# им сможет воспользоваться кто угодно.
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("Ошибка: не задана переменная окружения TOKEN.")
    print("Установите её перед запуском, например: export TOKEN='ваш_токен'")
    sys.exit(1)

# Chat ID администратора, которому будут приходить результаты прохождения теста.
ADMIN_ID = 7845112670

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class Quiz(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()
    q6 = State()
    q7 = State()
    q8 = State()
    q9 = State()
    q10 = State()


QUESTIONS = [
    {
        "text": "1. Главная разница между инвестором и трейдером:",
        "options": [
            "A) Инвестор зарабатывает на росте бизнеса и времени (долго держит), трейдер — на колебаниях цены «здесь и сейчас»",
            "B) Инвестор зарабатывает на колебаниях цены в коротком сроке, трейдер — на росте бизнеса за годы",
            "C) Оба делают одно и то же, просто называют по-разному",
        ],
        "correct": "A",
    },
    {
        "text": "2. Какой стиль трейдинга описан как «рыбалка с удочкой на весь день, к вечеру все сделки закрыты»?",
        "options": ["A) Скальпинг", "B) Позиционная торговля", "C) Интрадей"],
        "correct": "C",
    },
    {
        "text": "3. Если у тебя меньше часа в день на графики, какой стиль, скорее всего, подойдёт?",
        "options": ["A) Свинг или позиционка", "B) Скальпинг", "C) Интрадей с 200 сделками"],
        "correct": "A",
    },
    {
        "text": "4. Зелёная свеча (обычно) означает:",
        "options": [
            "A) Цена закрылась ниже открытия (день/период закончился хуже)",
            "B) Цена вообще не двигалась",
            "C) Цена закрылась выше открытия (день/период закончился лучше)",
        ],
        "correct": "C",
    },
    {
        "text": "5. Что показывают тени (фитили) свечи?",
        "options": [
            "A) Максимум и минимум цены за период (куда цена «выстреливала», но не удержалась)",
            "B) Только цвет свечи",
            "C) Только цену открытия",
        ],
        "correct": "A",
    },
    {
        "text": "6. Уровень поддержки — это:",
        "options": [
            "A) «Потолок», от которого цена отскакивает вниз",
            "B) «Пол», от которого цена отскакивает вверх (покупатели выкупают)",
            "C) Любая круглая цифра на графике",
        ],
        "correct": "B",
    },
    {
        "text": "7. Что часто происходит, когда цена пробивает уровень поддержки?",
        "options": [
            "A) Бывшая поддержка часто становится сопротивлением",
            "B) Уровень остаётся поддержкой навсегда",
            "C) Цена больше никогда не возвращается к этому уровню",
        ],
        "correct": "A",
    },
    {
        "text": "8. Какая эмоция чаще всего заставляет закрывать прибыльную сделку слишком рано?",
        "options": ["A) Жадность", "B) Скука", "C) Страх"],
        "correct": "C",
    },
    {
        "text": "9. Что такое «revenge trading» (отыгрывание убытка)?",
        "options": [
            "A) Спокойный анализ после убытка и вход по плану",
            "B) Сразу после убытка открывать новую сделку «чтобы отбить», часто без анализа и с увеличенным риском",
            "C) Ведение дневника сделок",
        ],
        "correct": "B",
    },
    {
        "text": "10. Что помогает лучше всего справляться с эмоциями в трейдинге?",
        "options": [
            "A) Торговать «по ощущениям» в моменте",
            "B) Смотреть чужие результаты в интернете и копировать их",
            "C) Заранее написанный торговый план + дневник сделок + пауза после убытков",
        ],
        "correct": "C",
    },
]


def make_keyboard(options):
    buttons = [[KeyboardButton(text=opt)] for opt in options]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


async def process_answer(message: types.Message, state: FSMContext, question_index: int, next_state):
    data = await state.get_data()
    score = data.get("score", 0)
    user_answer = message.text.strip()
    correct = QUESTIONS[question_index]["correct"]
    is_correct = user_answer.upper().startswith(correct)
    if is_correct:
        score += 1
        feedback = "✅ Правильно!"
    else:
        feedback = "❌ Неправильно!"
    await state.update_data(score=score)
    await message.answer(feedback)
    if question_index < 9:
        await state.set_state(next_state)
        q = QUESTIONS[question_index + 1]
        await message.answer(q["text"] + "\n\n" + "\n".join(q["options"]), reply_markup=make_keyboard(q["options"]))
    else:
        await state.clear()
        result = f"🏁 Тест завершён!\n\nПравильных ответов: <b>{score} из 10</b>\n\n"
        if score >= 7:
            result += "🎉 <b>Поздравляю! Ты допущен к полноценной сессии.</b>\nНапиши @ElenaSorokinaCrypto, чтобы продолжить."
        else:
            result += "📚 Нужно заново изучить материал и пройти тест ещё раз.\nКогда будешь готов — снова напиши /test"
        await message.answer(result, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

        # Уведомляем администратора о результате прохождения теста.
        user = message.from_user
        username = f"@{user.username}" if user.username else "(без username)"
        admin_text = (
            f"📊 Новый результат теста\n\n"
            f"Пользователь: {user.full_name} {username}\n"
            f"ID: <code>{user.id}</code>\n"
            f"Результат: <b>{score} из 10</b>\n"
            f"Допущен: {'✅ да' if score >= 7 else '❌ нет'}"
        )
        try:
            await message.bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        except Exception as e:
            logger.warning("Не удалось отправить результат админу: %s", e)


def register_handlers(dp: Dispatcher):
    @dp.message(Command("start"))
    async def start(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer(
            "🔥 Привет! Это тест по материалу «Трейдинг vs Инвестиции».\n\n"
            "Всего 10 вопросов.\n"
            "Чтобы быть допущенным к полноценной сессии — нужно правильно ответить минимум на 7.\n\n"
            "Готов? Нажми /test чтобы начать.",
            reply_markup=ReplyKeyboardRemove(),
        )

    @dp.message(Command("test"))
    async def test(message: types.Message, state: FSMContext):
        await state.clear()
        await state.update_data(score=0)
        await state.set_state(Quiz.q1)
        q = QUESTIONS[0]
        await message.answer(q["text"] + "\n\n" + "\n".join(q["options"]), reply_markup=make_keyboard(q["options"]))

    @dp.message(Quiz.q1)
    async def q1(message: types.Message, state: FSMContext):
        await process_answer(message, state, 0, Quiz.q2)

    @dp.message(Quiz.q2)
    async def q2(message: types.Message, state: FSMContext):
        await process_answer(message, state, 1, Quiz.q3)

    @dp.message(Quiz.q3)
    async def q3(message: types.Message, state: FSMContext):
        await process_answer(message, state, 2, Quiz.q4)

    @dp.message(Quiz.q4)
    async def q4(message: types.Message, state: FSMContext):
        await process_answer(message, state, 3, Quiz.q5)

    @dp.message(Quiz.q5)
    async def q5(message: types.Message, state: FSMContext):
        await process_answer(message, state, 4, Quiz.q6)

    @dp.message(Quiz.q6)
    async def q6(message: types.Message, state: FSMContext):
        await process_answer(message, state, 5, Quiz.q7)

    @dp.message(Quiz.q7)
    async def q7(message: types.Message, state: FSMContext):
        await process_answer(message, state, 6, Quiz.q8)

    @dp.message(Quiz.q8)
    async def q8(message: types.Message, state: FSMContext):
        await process_answer(message, state, 7, Quiz.q9)

    @dp.message(Quiz.q9)
    async def q9(message: types.Message, state: FSMContext):
        await process_answer(message, state, 8, Quiz.q10)

    @dp.message(Quiz.q10)
    async def q10(message: types.Message, state: FSMContext):
        await process_answer(message, state, 9, None)


async def run_bot():
    """Один цикл поллинга. Возвращает управление, если поллинг завершился/упал."""
    bot = Bot(token=TOKEN, default=DefaultBotProperties())
    dp = Dispatcher(storage=MemoryStorage())
    register_handlers(dp)

    logger.info("Бот запущен...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


async def main():
    # Бесконечный цикл с реконнектом: если пропадёт сеть или Telegram API
    # вернёт временную ошибку, бот не упадёт насовсем, а попробует снова
    # через паузу. Это и есть работа "24/7" на уровне самого процесса —
    # хостинг (Railway/Render/systemd) в свою очередь перезапускает сам
    # процесс, если упадёт он целиком.
    backoff = 5
    while True:
        try:
            await run_bot()
            break  # dp.start_polling завершился штатно (например, Ctrl+C)
        except TelegramRetryAfter as e:
            logger.warning("Превышен лимит запросов, ждём %s сек.", e.retry_after)
            await asyncio.sleep(e.retry_after)
        except TelegramNetworkError as e:
            logger.warning("Проблема с сетью: %s. Переподключение через %s сек.", e, backoff)
            await asyncio.sleep(backoff)
        except Exception as e:
            logger.exception("Неожиданная ошибка: %s. Переподключение через %s сек.", e, backoff)
            await asyncio.sleep(backoff)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен.")
