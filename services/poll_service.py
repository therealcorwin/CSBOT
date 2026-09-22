"""Service de gestion des sondages certifiés (contrôle 1 vote par appartement)."""

from typing import Dict, List, Optional, Tuple
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from database.models import Apartment, Occupant, Poll, PollVote


class PollService:
    @staticmethod
    async def create_poll(
        session: AsyncSession,
        title: str,
        options: List[str],
        created_by_user_id: int,
        description: Optional[str] = None,
        poll_type: str = "FORMAL_APARTMENT",
    ) -> Poll:
        """Crée un nouveau sondage officiel."""
        poll = Poll(
            title=title,
            description=description,
            options={"choices": options},
            poll_type=poll_type,
            created_by_user_id=created_by_user_id,
            is_active=True,
        )
        session.add(poll)
        await session.flush()
        return poll

    @staticmethod
    async def get_active_poll(session: AsyncSession) -> Optional[Poll]:
        """Récupère le dernier sondage actif en cours."""
        stmt = (
            select(Poll)
            .where(Poll.is_active.is_(True))
            .options(selectinload(Poll.votes))
            .order_by(Poll.created_at.desc())
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def cast_vote(
        session: AsyncSession,
        poll_id: int,
        user_id: int,
        option_index: int,
    ) -> Tuple[bool, str]:
        """Enregistre le vote d'un résident en garantissant 1 vote par appartement."""
        # 1. Vérifier si l'utilisateur est rattaché à un appartement actif
        stmt_occ = (
            select(Apartment)
            .join(Occupant, Occupant.apartment_id == Apartment.id)
            .where(Occupant.user_id == user_id, Occupant.is_active.is_(True))
        )
        res_occ = await session.execute(stmt_occ)
        apartment = res_occ.scalar_one_or_none()

        if not apartment:
            return False, "Votre profil n'est rattaché à aucun appartement validé."

        # 2. Vérifier si l'appartement a déjà voté
        stmt_vote = select(PollVote).where(
            PollVote.poll_id == poll_id,
            PollVote.apartment_id == apartment.id,
        )
        res_vote = await session.execute(stmt_vote)
        existing_vote = res_vote.scalar_one_or_none()

        if existing_vote:
            return False, f"Un vote a déjà été enregistré pour l'appartement {apartment.number}."

        # 3. Enregistrer le vote
        try:
            vote = PollVote(
                poll_id=poll_id,
                apartment_id=apartment.id,
                user_id=user_id,
                selected_option=option_index,
            )
            session.add(vote)
            await session.flush()
            return True, f"Vote pris en compte avec succès pour le lot {apartment.number} !"
        except IntegrityError:
            await session.rollback()
            return False, "Un vote simultané a déjà été comptabilisé pour ce lot."

    @staticmethod
    async def get_results(session: AsyncSession, poll_id: int) -> Dict:
        """Calcule les résultats détaillés du sondage pour le Conseil Syndical."""
        stmt = (
            select(Poll)
            .where(Poll.id == poll_id)
            .options(selectinload(Poll.votes).selectinload(PollVote.apartment))
        )
        res = await session.execute(stmt)
        poll = res.scalar_one_or_none()

        if not poll:
            return {}

        choices = poll.options.get("choices", [])
        counts = {i: 0 for i in range(len(choices))}
        voted_apartments = []

        for v in poll.votes:
            if v.selected_option in counts:
                counts[v.selected_option] += 1
            if v.apartment:
                voted_apartments.append(v.apartment.number)

        return {
            "title": poll.title,
            "total_votes": len(poll.votes),
            "choices": choices,
            "counts": counts,
            "voted_lots": sorted(voted_apartments),
        }

