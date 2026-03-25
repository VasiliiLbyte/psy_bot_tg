"""FSM states for the diagnostic flow."""

from aiogram.fsm.state import State, StatesGroup


class DiagnosticStates(StatesGroup):
    """Stages aligned with project-plan: symptom → context → evaluation → recommendations."""

    symptom_collection = State()
    context_collection = State()
    evaluation = State()
    recommendations = State()
