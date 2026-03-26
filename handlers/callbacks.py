"""Message handlers for action keyboard buttons."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, ReplyKeyboardRemove

import storage
from safety import BRIEF_NON_MEDICAL_NOTICE
from states import DiagnosticStates

router = Router()

_START_PROMPT = (
    "Опишите, что вас беспокоит: основные симптомы или жалобы одним сообщением."
)

_NEXT_STEPS_TEXT = (
    "## Что делать дальше\n\n"
    "1) Если состояние ухудшается или есть мысли о самоповреждении — обратитесь за срочной помощью.\n"
    "2) Запишитесь к специалисту: начните с терапевта/врача общей практики, "
    "или сразу к психиатру/психотерапевту (по ситуации).\n"
    "3) Подготовьтесь к приёму:\n"
    "- кратко опишите симптомы (когда начались, что усиливает/уменьшает)\n"
    "- список лекарств/добавок, дозировки\n"
    "- выписки/анализы (если есть)\n"
    "- вопросы, которые хотите обсудить\n\n"
    "Горячие линии (РФ):\n"
    "- 8-800-2000-122 — бесплатная психологическая помощь (круглосуточно)\n"
)


def recommendations_actions_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔄 Новый опрос"),
            ],
            [
                KeyboardButton(text="❓ Задать вопрос"),
                KeyboardButton(text="📋 Что делать дальше?"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


@router.message(
    StateFilter(DiagnosticStates.recommendations, DiagnosticStates.followup),
    F.text == "🔄 Новый опрос",
)
async def on_restart(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    uid = message.from_user.id
    await state.clear()
    await storage.reset_user_session(uid)
    await state.set_state(DiagnosticStates.symptom_collection)
    await message.answer(
        "Бот для первичной психоневрологической анкетирования.\n\n"
        f"{BRIEF_NON_MEDICAL_NOTICE}\n\n"
        + _START_PROMPT,
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(
    StateFilter(DiagnosticStates.recommendations, DiagnosticStates.followup),
    F.text == "❓ Задать вопрос",
)
async def on_followup(message: Message, state: FSMContext) -> None:
    await state.set_state(DiagnosticStates.followup)
    await message.answer(
        "Задайте уточняющий вопрос одним сообщением. Я отвечу с учётом контекста диалога."
    )


@router.message(
    StateFilter(DiagnosticStates.recommendations, DiagnosticStates.followup),
    F.text == "📋 Что делать дальше?",
)
async def on_next_steps(message: Message) -> None:
    await message.answer(_NEXT_STEPS_TEXT)

