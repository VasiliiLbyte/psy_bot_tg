"""Callback query handlers for inline actions."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

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


def recommendations_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Новый опрос",
                    callback_data="action:restart",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❓ Задать вопрос",
                    callback_data="action:followup",
                ),
                InlineKeyboardButton(
                    text="📋 Что делать дальше?",
                    callback_data="action:next_steps",
                ),
            ],
        ]
    )


@router.callback_query(F.data == "action:restart")
async def cb_restart(query: CallbackQuery, state: FSMContext) -> None:
    if query.from_user is None:
        return
    uid = query.from_user.id
    await state.clear()
    await storage.reset_user_session(uid)
    await state.set_state(DiagnosticStates.symptom_collection)
    await query.message.answer(
        "Бот для первичной психоневрологической анкетирования.\n\n"
        f"{BRIEF_NON_MEDICAL_NOTICE}\n\n"
        + _START_PROMPT
    )
    await query.answer()


@router.callback_query(F.data == "action:followup")
async def cb_followup(query: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DiagnosticStates.followup)
    if query.message:
        await query.message.answer(
            "Задайте уточняющий вопрос одним сообщением. Я отвечу с учётом контекста диалога."
        )
    await query.answer()


@router.callback_query(F.data == "action:next_steps")
async def cb_next_steps(query: CallbackQuery) -> None:
    if query.message:
        await query.message.answer(_NEXT_STEPS_TEXT)
    await query.answer()

