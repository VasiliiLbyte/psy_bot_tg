"""Plain message handlers (FSM)."""

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import storage
from states import DiagnosticStates

router = Router()

_CONTEXT_PROMPT = (
    "Расскажите кратко о контексте: когда началось, что предшествовало, "
    "есть ли хронические заболевания (по желанию)."
)

_EVAL_PLACEHOLDER = (
    "Сбор данных завершён. На следующем этапе разработки здесь будет "
    "автоматическая оценка с помощью модели (OpenRouter)."
)

_DISCLAIMER = (
    "Это не медицинская консультация. Обратитесь к специалисту. "
    "При острых состояниях вызывайте скорую помощь (112 / 103)."
)


@router.message(DiagnosticStates.symptom_collection, F.text)
async def on_symptoms(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    uid = message.from_user.id
    text = message.text.strip()
    await storage.set_collected_field(uid, "symptoms", text)
    await storage.append_history(uid, "user", text)
    await state.set_state(DiagnosticStates.context_collection)
    reply = _CONTEXT_PROMPT
    await storage.append_history(uid, "assistant", reply)
    await message.answer(reply)


@router.message(DiagnosticStates.context_collection, F.text)
async def on_context(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    uid = message.from_user.id
    text = message.text.strip()
    await storage.set_collected_field(uid, "life_context", text)
    await storage.append_history(uid, "user", text)
    await state.set_state(DiagnosticStates.evaluation)
    await message.answer(_EVAL_PLACEHOLDER)
    await storage.append_history(uid, "assistant", _EVAL_PLACEHOLDER)

    await state.set_state(DiagnosticStates.recommendations)
    rec = (
        "По результатам первичного сбора данных рекомендуется очная консультация "
        f"с врачом (психиатр / невролог по показаниям).\n\n{_DISCLAIMER}"
    )
    await message.answer(rec)
    await storage.append_history(uid, "assistant", rec)


@router.message(
    StateFilter(
        DiagnosticStates.symptom_collection,
        DiagnosticStates.context_collection,
    ),
    ~F.text,
)
async def need_text_in_collection(message: Message) -> None:
    await message.answer("Пожалуйста, отправьте ответ текстом.")


@router.message(StateFilter(DiagnosticStates.evaluation))
async def evaluation_hold(message: Message) -> None:
    """Reserved for stage 3 (LLM); today state is usually skipped immediately."""
    await message.answer(
        "Подождите, идёт подготовка ответа. Если зависло — отправьте /start."
    )


@router.message(StateFilter(DiagnosticStates.recommendations))
async def survey_completed(message: Message) -> None:
    await message.answer("Опрос завершён. Чтобы начать заново: /start.")
