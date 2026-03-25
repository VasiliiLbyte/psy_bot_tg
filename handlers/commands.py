"""Command handlers."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import storage
from states import DiagnosticStates

router = Router()

_START_PROMPT = (
    "Опишите, что вас беспокоит: основные симптомы или жалобы одним сообщением."
)


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.from_user is None:
        return
    uid = message.from_user.id
    await storage.reset_user_session(uid)
    await state.set_state(DiagnosticStates.symptom_collection)
    await message.answer(
        "Бот для первичной психоневрологической анкетирования.\n\n" + _START_PROMPT
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Доступные команды:\n"
        "/start — начать опрос заново\n"
        "/help — эта справка\n\n"
        "После /start бот задаст несколько вопросов по шагам."
    )
