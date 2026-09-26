"""Modèles de base de données relationnelle pour CSBOT (SQLAlchemy 2.0)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """Utilisateur Telegram (résident, copropriétaire ou membre du CS)."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="Telegram User ID")
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(64), default="")
    last_name: Mapped[str] = mapped_column(String(64), default="")
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Statut du résident
    status: Mapped[str] = mapped_column(
        Enum("OWNER_OCCUPANT", "TENANT", "OWNER_NON_RESIDENT", name="occupant_status_enum"),
        default="OWNER_OCCUPANT"
    )

    # Permissions et rôles
    is_cs_member: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="Nom / pseudo du validateur")
    approved_by_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="ID Telegram du validateur")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="Date et heure de validation")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relations
    occupancies: Mapped[list["Occupant"]] = relationship("Occupant", back_populates="user", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="user")
    ag_ideas: Mapped[list["AGIdea"]] = relationship("AGIdea", back_populates="user")
    solidarity_items: Mapped[list["SolidarityItem"]] = relationship("SolidarityItem", back_populates="user")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or (self.username or str(self.id))


class Apartment(Base):
    """Appartement ou lot de la copropriété."""
    __tablename__ = "apartments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="Numéro de porte / lot")
    floor: Mapped[int] = mapped_column(Integer, default=0)
    building: Mapped[str] = mapped_column(String(32), default="A")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    occupants: Mapped[list["Occupant"]] = relationship("Occupant", back_populates="apartment")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="apartment")
    poll_votes: Mapped[list["PollVote"]] = relationship("PollVote", back_populates="apartment")


class Occupant(Base):
    """Liaison entre un utilisateur et un appartement (gestion des déménagements et co-occupants)."""
    __tablename__ = "occupants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    apartment_id: Mapped[int] = mapped_column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    moved_in_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    moved_out_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    apartment: Mapped["Apartment"] = relationship("Apartment", back_populates="occupants")
    user: Mapped["User"] = relationship("User", back_populates="occupancies")


class Ticket(Base):
    """Ticket de signalement de panne ou d'incident."""
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    apartment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("apartments.id", ondelete="SET NULL"), nullable=True)
    category: Mapped[str] = mapped_column(String(64), comment="Ascenseur, Plomberie, Electricite, etc.")
    description: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    status: Mapped[str] = mapped_column(
        Enum("OPEN", "SENT_TO_SYNDIC", "IN_PROGRESS", "RESOLVED", "CANCELLED", name="ticket_status_enum"),
        default="OPEN",
        index=True
    )

    handled_by_cs_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sent_to_syndic_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_reminder_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    external_ticket_url: Mapped[str | None] = mapped_column(String(256), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user: Mapped[Optional["User"]] = relationship("User", back_populates="tickets")
    apartment: Mapped[Optional["Apartment"]] = relationship("Apartment", back_populates="tickets")


class VendorVisit(Base):
    """Carnet de passage des prestataires dans la copropriété."""
    __tablename__ = "vendor_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_name: Mapped[str] = mapped_column(String(128))
    service_type: Mapped[str] = mapped_column(String(64))
    intervention_summary: Mapped[str] = mapped_column(Text)
    reported_by_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    visit_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Poll(Base):
    """Sondage d'avis ou consultation officielle par appartement."""
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    options: Mapped[dict] = mapped_column(JSON, comment="Liste des choix possibles")
    poll_type: Mapped[str] = mapped_column(String(32), default="FORMAL_APARTMENT")  # FORMAL_APARTMENT ou QUICK
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_user_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    closes_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    votes: Mapped[list["PollVote"]] = relationship("PollVote", back_populates="poll", cascade="all, delete-orphan")


class PollVote(Base):
    """Vote individuel pour un sondage officiel (strictement 1 vote par appartement)."""
    __tablename__ = "poll_votes"
    __table_args__ = (
        UniqueConstraint("poll_id", "apartment_id", name="uq_poll_apartment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    poll_id: Mapped[int] = mapped_column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), index=True)
    apartment_id: Mapped[int] = mapped_column(Integer, ForeignKey("apartments.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    selected_option: Mapped[int] = mapped_column(Integer)
    voted_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    poll: Mapped["Poll"] = relationship("Poll", back_populates="votes")
    apartment: Mapped["Apartment"] = relationship("Apartment", back_populates="poll_votes")


class AGIdea(Base):
    """Boîte à idées / Résolutions citoyennes pour la prochaine AG."""
    __tablename__ = "ag_ideas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED")  # PROPOSED, REVIEWED, INCLUDED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="ag_ideas")


class SolidarityItem(Base):
    """Annonces d'entraide entre résidents (dons ou prêts de matériel)."""
    __tablename__ = "solidarity_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    item_type: Mapped[str] = mapped_column(String(32), default="LOAN")  # LOAN ou DONATION
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    photo_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="solidarity_items")
