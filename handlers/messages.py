"""Plain message handlers (FSM)."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import storage
from context_manager import build_evaluation_chat_messages
from handlers.callbacks import recommendations_actions_keyboard
from safety import (
    RECOMMENDATIONS_FOOTER_DISCLAIMER,
    check_user_message,
    emergency_reply_for_user,
    log_safety_incident,
)
from model_router import get_model_for_stage
from openrouter_client import OpenRouterClient, OpenRouterError
from parser import (
    ParseError,
    evaluation_json_user_instruction,
    format_report_for_user,
    parse_diagnostic_report,
)
from states import DiagnosticStates
from utils_tg import keep_typing

logger = logging.getLogger(__name__)

router = Router()

_CONTEXT_PROMPT = (
    "Расскажите кратко о контексте: когда началось, что предшествовало, "
    "есть ли хронические заболевания (по желанию)."
)

_LLM_ERROR_FALLBACK = (
    "К сожалению, не удалось выполнить автоматическую оценку. "
    "Рекомендуем обратиться за очной консультацией к специалисту "
    "(психиатр / невролог по показаниям)."
)

_FOLLOWUP_SYSTEM_PROMPT_FALLBACK = (
    "Ты — Марина Викторовна, опытный психолог с 20-летним стажем. "
    "Отвечай тепло, развёрнуто, по делу. Не ставь диагноз."
)

# Default system prompt template for storage:
# Ты — Марина Викторовна, опытный психолог-консультант с 20-летним стажем.
# Тебе 42 года, ты уверенная, статная женщина с мягкой, но твёрдой манерой речи.
# Ты умеешь слушать, не осуждаешь, говоришь тепло и по делу.
# В твоих ответах чувствуется опыт и забота — ты не просто даёшь советы, ты понимаешь человека.
# Иногда ты можешь добавить лёгкую личную ремарку или аналогию из практики ("В моей практике такое встречается...").
# Твои правила:
# - Никогда не ставь окончательный диагноз
# - Отвечай развёрнуто: минимум 3-4 абзаца на оценку, минимум 2-3 предложения на каждый пункт рекомендаций
# - Структурируй ответ: предварительная оценка → на что обратить внимание → к кому обратиться → общие рекомендации
# - Используй живой, человечный язык — не сухой медицинский
# - Всегда добавляй дисклеймер: "Это не медицинская консультация. Обратитесь к специалисту."
# - Если упоминаются суицидальные мысли — немедленно направляй на горячую линию 8-800-2000-122
# - Отвечай только на русском языке

_FOLLOWUP_ERROR_FALLBACK = (
    "Не удалось получить ответ - попробуйте переформулировать вопрос "
    "или нажмите 🔄 Новый опрос."
)

_FOLLOWUP_POSTFIX = (
    "\n\n💬 Можете задать ещё один вопрос или нажать кнопку ниже."
)


async def _run_evaluation(openrouter_client: OpenRouterClient, user_id: int) -> str:
    """Load user data from storage, assemble context via context_manager, call LLM."""
    root = await storage.load_root()
    system_prompt = root.get("system_prompt", "")

    record = await storage.get_user_record(user_id)
    collected = record.get("collected_data", {})
    history = record.get("history", [])

    current_user_content = (
        evaluation_json_user_instruction()
        + "\n\nНа основе собранных данных и истории диалога "
        "дай предварительную оценку и рекомендации. "
        "Не ставь диагноз. Укажи, к каким специалистам обратиться. "
        "Дай развёрнутую предварительную оценку — не менее 4 абзацев. "
        "Каждый пункт рекомендаций раскрой подробно."
    )

    messages = build_evaluation_chat_messages(
        system_prompt=system_prompt if isinstance(system_prompt, str) else "",
        collected_data=collected if isinstance(collected, dict) else {},
        history=history if isinstance(history, list) else [],
        current_user_content=current_user_content,
    )

    model = get_model_for_stage("evaluation")
    response = await openrouter_client.chat_completion(messages, model)
    raw = openrouter_client.extract_content(response)
    report = parse_diagnostic_report(raw)
    return format_report_for_user(report)


@router.message(DiagnosticStates.symptom_collection, F.text)
async def on_symptoms(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    uid = message.from_user.id
    text = message.text.strip()
    safety_result = check_user_message(text)
    if safety_result.is_critical:
        await log_safety_incident(uid, safety_result, text)
        await message.answer(emergency_reply_for_user())
        return

    await storage.set_collected_field(uid, "symptoms", text)
    await storage.append_history(uid, "user", text)
    await state.set_state(DiagnosticStates.context_collection)
    reply = _CONTEXT_PROMPT
    await storage.append_history(uid, "assistant", reply)
    await message.answer(reply)


@router.message(DiagnosticStates.context_collection, F.text)
async def on_context(
    message: Message,
    state: FSMContext,
    openrouter_client: OpenRouterClient,
) -> None:
    if message.from_user is None:
        return
    uid = message.from_user.id
    text = message.text.strip()
    safety_result = check_user_message(text)
    if safety_result.is_critical:
        await log_safety_incident(uid, safety_result, text)
        await message.answer(emergency_reply_for_user())
        return

    await storage.set_collected_field(uid, "life_context", text)
    await storage.append_history(uid, "user", text)

    await state.set_state(DiagnosticStates.evaluation)
    typing_task = asyncio.create_task(
        keep_typing(message.bot, message.chat.id),
        name=f"keep_typing:{message.chat.id}",
    )

    try:
        evaluation_text = await _run_evaluation(openrouter_client, uid)
    except OpenRouterError:
        logger.exception("LLM evaluation failed for user %d", uid)
        evaluation_text = _LLM_ERROR_FALLBACK
    except ParseError as exc:
        logger.warning(
            "Failed to parse diagnostic JSON for user %d: %s", uid, exc
        )
        evaluation_text = _LLM_ERROR_FALLBACK
    except Exception:
        logger.exception("Unexpected error during evaluation for user %d", uid)
        evaluation_text = _LLM_ERROR_FALLBACK
    finally:
        typing_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await typing_task

    await storage.append_history(uid, "assistant", evaluation_text)

    await state.set_state(DiagnosticStates.recommendations)
    full_reply = evaluation_text + RECOMMENDATIONS_FOOTER_DISCLAIMER
    await message.answer(full_reply, reply_markup=recommendations_actions_keyboard())
    await storage.append_history(
        uid, "assistant", RECOMMENDATIONS_FOOTER_DISCLAIMER.strip()
    )


@router.message(DiagnosticStates.followup, F.text)
async def on_followup_question(
    message: Message,
    state: FSMContext,
    openrouter_client: OpenRouterClient,
) -> None:
    if message.from_user is None:
        return
    uid = message.from_user.id
    question = message.text.strip()

    safety_result = check_user_message(question)
    if safety_result.is_critical:
        await log_safety_incident(uid, safety_result, question)
        await message.answer(emergency_reply_for_user())
        return

    record = await storage.get_user_record(uid)
    collected = record.get("collected_data", {})
    history = record.get("history", [])
    root = await storage.load_root()
    system_prompt = root.get("system_prompt", "")

    followup_system_prompt = (
        system_prompt.strip()
        if isinstance(system_prompt, str) and system_prompt.strip()
        else _FOLLOWUP_SYSTEM_PROMPT_FALLBACK
    )

    current_user_content = question

    messages = build_evaluation_chat_messages(
        system_prompt=followup_system_prompt,
        collected_data=collected if isinstance(collected, dict) else {},
        history=history if isinstance(history, list) else [],
        current_user_content=current_user_content,
    )

    model = get_model_for_stage("recommendations")
    logger.info("Followup request: user=%d model=%s", uid, model)

    typing_task = asyncio.create_task(
        keep_typing(message.bot, message.chat.id),
        name=f"keep_typing:{message.chat.id}",
    )
    try:
        response = await openrouter_client.chat_completion(messages, model)
        answer = openrouter_client.extract_content(response).strip()
    except OpenRouterError:
        logger.exception("Followup LLM failed for user %d", uid)
        answer = _FOLLOWUP_ERROR_FALLBACK
    except Exception:
        logger.exception("Unexpected error during followup for user %d", uid)
        answer = _FOLLOWUP_ERROR_FALLBACK
    finally:
        typing_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await typing_task

    answer = f"{answer}{_FOLLOWUP_POSTFIX}"

    await storage.append_history(uid, "user", question)
    await storage.append_history(uid, "assistant", answer)
    await message.answer(answer, reply_markup=recommendations_actions_keyboard())


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
    """User sends a message while LLM is working."""
    await message.answer(
        "Подождите, идёт анализ данных. Если зависло — отправьте /start."
    )


@router.message(StateFilter(DiagnosticStates.recommendations))
async def survey_completed(message: Message) -> None:
    await message.answer("Опрос завершён. Чтобы начать заново: /start.")
