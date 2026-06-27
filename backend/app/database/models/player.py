"""Player ORM model."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.database.base import Base


class Player(Base):
    """Represents a registered tennis player."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Preferences
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)  # "en" | "uk" | "ru"
    skill_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_area: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preferred_courts: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list stored as text

    # Availability
    available_now: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Stats
    rating: Mapped[float] = mapped_column(Float, default=1000.0, nullable=False)
    matches_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    created_games: Mapped[list["Game"]] = relationship(  # noqa: F821
        "Game", back_populates="creator", foreign_keys="Game.creator_id"
    )
    game_participations: Mapped[list["GamePlayer"]] = relationship(  # noqa: F821
        "GamePlayer", back_populates="player"
    )

    @property
    def is_profile_complete(self) -> bool:
        """Return True when mandatory onboarding fields are filled."""
        return all(
            [
                self.language is not None,
                self.skill_level is not None,
                self.home_area is not None,
                self.preferred_courts is not None,
            ]
        )

    def __repr__(self) -> str:
        return f"<Player id={self.id} telegram_id={self.telegram_id} name={self.first_name!r}>"
