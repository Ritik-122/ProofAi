import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    wallet_address: Mapped[str] = mapped_column(String(42), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    challenge_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    challenge_message: Mapped[str | None] = mapped_column(String(1200))
    challenge_issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    challenge_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


def initialize_database() -> None:
    """Explicit bootstrap for the first feature; never mutate schema on API startup."""
    from app.config import Settings

    engine = create_engine(Settings().database_url)
    Base.metadata.create_all(engine)
    engine.dispose()


if __name__ == "__main__":
    initialize_database()
