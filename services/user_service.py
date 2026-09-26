"""Service de gestion des utilisateurs, des appartements et des déménagements."""

from datetime import datetime

from loguru import logger
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Apartment, Occupant, User


class UserService:
    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.occupancies).selectinload(Occupant.apartment)
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        user_id: int,
        username: str | None = None,
        first_name: str = "",
        last_name: str = "",
    ) -> User:
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            session.add(user)
            await session.flush()
        else:
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
            if last_name and user.last_name != last_name:
                user.last_name = last_name
        return user

    @staticmethod
    async def submit_onboarding(
        session: AsyncSession,
        user_id: int,
        data: dict,
    ) -> tuple[User, Apartment]:
        """Enregistre les données d'onboarding soumises par un résident."""
        user = await UserService.get_or_create_user(
            session=session,
            user_id=user_id,
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
        )
        user.phone = data.get("phone")
        user.email = data.get("email")
        user.status = data.get("status", "OWNER_OCCUPANT")

        # Recherche ou création de l'appartement
        apt_number = str(data.get("apartment_number", "")).strip().upper()
        floor = int(data.get("floor", 0))
        building = str(data.get("building", "A")).strip().upper()

        stmt = select(Apartment).where(Apartment.number == apt_number)
        res = await session.execute(stmt)
        apartment = res.scalar_one_or_none()

        if not apartment:
            apartment = Apartment(number=apt_number, floor=floor, building=building)
            session.add(apartment)
            await session.flush()
        else:
            apartment.floor = floor
            apartment.building = building

        # Création ou activation de l'occupant
        stmt_occ = select(Occupant).where(
            Occupant.apartment_id == apartment.id,
            Occupant.user_id == user.id,
        )
        res_occ = await session.execute(stmt_occ)
        occupant = res_occ.scalar_one_or_none()

        if not occupant:
            occupant = Occupant(
                apartment_id=apartment.id,
                user_id=user.id,
                is_active=True,
                moved_in_at=datetime.now(),
            )
            session.add(occupant)
        else:
            occupant.is_active = True
            occupant.moved_out_at = None

        await session.flush()
        return user, apartment

    @staticmethod
    async def approve_user(
        session: AsyncSession,
        user_id: int,
        approved_by: str | None = None,
        approved_by_id: int | None = None,
    ) -> User | None:
        """Valide l'inscription d'un résident par le Conseil Syndical."""
        user = await UserService.get_user_by_id(session, user_id)
        if user:
            user.is_approved = True
            user.approved_by = approved_by
            user.approved_by_id = approved_by_id
            user.approved_at = datetime.now()
            await session.flush()
            val_info = []
            if approved_by:
                val_info.append(approved_by)
            if approved_by_id:
                val_info.append(f"ID Telegram: {approved_by_id}")
            val_text = f" par {', '.join(val_info)}" if val_info else ""
            logger.info(f"Résident {user.id} ({user.full_name}) validé avec succès{val_text}.")
        return user

    @staticmethod
    async def reject_user(session: AsyncSession, user_id: int) -> User | None:
        """Refuse l'inscription d'un utilisateur."""
        user = await UserService.get_user_by_id(session, user_id)
        if user:
            user.is_approved = False
            # Désactive également ses occupations
            for occ in user.occupancies:
                occ.is_active = False
            await session.flush()
        return user

    @staticmethod
    async def move_out_user(session: AsyncSession, user_id: int) -> bool:
        """Déménagement d'un résident : désactivation de l'occupation et radiation."""
        user = await UserService.get_user_by_id(session, user_id)
        if not user:
            return False

        user.is_approved = False
        now = datetime.now()
        for occ in user.occupancies:
            occ.is_active = False
            occ.moved_out_at = now

        await session.flush()
        logger.info(f"Déménagement enregistré pour l'utilisateur {user_id}.")
        return True

    @staticmethod
    async def get_active_apartment_for_user(session: AsyncSession, user_id: int) -> Apartment | None:
        """Récupère l'appartement actif d'un utilisateur."""
        stmt = (
            select(Apartment)
            .join(Occupant, Occupant.apartment_id == Apartment.id)
            .where(Occupant.user_id == user_id, Occupant.is_active.is_(True))
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_pending_users(session: AsyncSession) -> list[User]:
        """Récupère tous les utilisateurs ayant soumis leur fiche et en attente de validation."""
        stmt = (
            select(User)
            .where(User.is_approved.is_(False), User.phone.is_not(None))
            .options(selectinload(User.occupancies).selectinload(Occupant.apartment))
            .order_by(User.created_at.desc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_occupants_by_apartment(session: AsyncSession, apt_number: str) -> list[tuple[User, Apartment]]:
        """Recherche tous les occupants actuels d'un numéro d'appartement."""
        stmt = (
            select(User, Apartment)
            .join(Occupant, Occupant.user_id == User.id)
            .join(Apartment, Apartment.id == Occupant.apartment_id)
            .where(
                Apartment.number == apt_number.strip().upper(),
                Occupant.is_active.is_(True),
            )
        )
        res = await session.execute(stmt)
        return list(res.all())

    @staticmethod
    async def search_residents_by_query(session: AsyncSession, query: str) -> list[tuple[User, Apartment | None]]:
        """Recherche un résident par son nom, prénom ou pseudo."""
        clean_q = f"%{query.strip()}%"
        stmt = (
            select(User, Apartment)
            .outerjoin(Occupant, (Occupant.user_id == User.id) & (Occupant.is_active.is_(True)))
            .outerjoin(Apartment, Apartment.id == Occupant.apartment_id)
            .where(
                or_(
                    User.first_name.ilike(clean_q),
                    User.last_name.ilike(clean_q),
                    User.username.ilike(clean_q),
                )
            )
        )
        res = await session.execute(stmt)
        return list(res.all())

    @staticmethod
    async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
        """Recherche un utilisateur par son @username exact (insensible à la casse)."""
        clean_username = username.lstrip("@").strip()
        stmt = (
            select(User)
            .where(func.lower(User.username) == clean_username.lower())
            .options(selectinload(User.occupancies).selectinload(Occupant.apartment))
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def promote_to_cs(session: AsyncSession, user_id: int) -> User | None:
        """Promeut un utilisateur au rôle de membre du Conseil Syndical."""
        user = await UserService.get_user_by_id(session, user_id)
        if user:
            user.is_cs_member = True
            user.is_approved = True
            await session.flush()
            logger.info(f"Utilisateur {user.id} ({user.full_name}) promu membre du Conseil Syndical.")
        return user

    @staticmethod
    async def demote_from_cs(session: AsyncSession, user_id: int) -> User | None:
        """Rétrograde un membre du Conseil Syndical en simple copropriétaire."""
        user = await UserService.get_user_by_id(session, user_id)
        if user:
            user.is_cs_member = False
            await session.flush()
            logger.info(f"Utilisateur {user.id} ({user.full_name}) rétrogradé en simple copropriétaire.")
        return user

    @staticmethod
    async def get_cs_members(session: AsyncSession) -> list[User]:
        """Récupère la liste de tous les membres du Conseil Syndical."""
        stmt = (
            select(User)
            .where(User.is_cs_member.is_(True))
            .options(selectinload(User.occupancies).selectinload(Occupant.apartment))
            .order_by(User.first_name, User.last_name)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())


