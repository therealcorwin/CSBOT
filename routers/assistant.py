"""Routeur de l'assistant documentaire IA (RAG sur le règlement de copro et n8n)."""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from services.llm.manager import llm_manager
from services.n8n_service import N8nService

assistant_router = Router(name="assistant_router")


class AssistantFSM(StatesGroup):
    waiting_question = State()


@assistant_router.message(F.text == "💬 Poser une question (IA)")
async def start_assistant(message: Message, state: FSMContext, is_approved: bool):
    """Démarre une session d'échange avec l'assistant IA de la copropriété."""
    if not is_approved:
        await message.answer("⚠️ Cette fonctionnalité est réservée aux résidents validés.")
        return

    await state.clear()
    await message.answer(
        "🤖 <b>ASSISTANT VIRTUEL DE LA COPROPRIÉTÉ</b>\n\n"
        "Je suis alimenté par les documents officiels de la résidence (Règlement de copropriété, PV d'AG, carnet pratique).\n\n"
        "Posez-moi votre question (ex : <i>'Quels sont les horaires autorisés pour les travaux bruyants ?'</i>, "
        "<i>'Comment obtenir un nouveau badge de parking ?'</i>, <i>'Puis-je installer une climatisation sur mon balcon ?'</i>) :",
        parse_mode="HTML"
    )
    await state.set_state(AssistantFSM.waiting_question)


@assistant_router.message(AssistantFSM.waiting_question, F.text)
async def process_question(message: Message, state: FSMContext):
    question = message.text.strip()
    if question.startswith("/"):
        await state.clear()
        return

    # Indicateur d'écriture Telegram
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # 1. Recherche principale via LLMManager (RAG local Gemini / Mistral)
    answer = await llm_manager.answer_condo_question(question)

    # 2. Recherche étendue via n8n si réponse incertaine ou document externe
    if ("je ne trouve pas" in answer.lower() or "consulter le conseil syndical" in answer.lower()):
        extended = await N8nService.query_extended_knowledge(question, user_id=message.from_user.id)
        if extended:
            answer += f"\n\n🔍 <i>Complément d'information extrait des archives :</i>\n{extended}"

    await message.answer(
        f"🤖 <b>Réponse de Georges Bot :</b>\n\n{answer}\n\n"
        "<i>Vous pouvez poser une autre question ou revenir au menu principal.</i>",
        parse_mode="HTML"
    )

