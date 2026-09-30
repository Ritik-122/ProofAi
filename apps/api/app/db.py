import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, Uuid, create_engine
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


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("creator_id", "request_id", name="uq_task_creator_request"),
        CheckConstraint("reward_wei > 0", name="ck_task_positive_reward"),
        CheckConstraint("status = 'AWAITING_FUNDING'", name="ck_task_initial_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    creator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    request_payload: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    template_id: Mapped[str] = mapped_column(String(80))
    repository_revision: Mapped[str] = mapped_column(String(80))
    repository_snapshot: Mapped[str] = mapped_column(Text)
    reward_wei: Mapped[str] = mapped_column(Numeric(78, 0).with_variant(String(78), "sqlite"))
    status: Mapped[str] = mapped_column(String(40))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canonical_payload: Mapped[str] = mapped_column(Text)
    task_hash: Mapped[str] = mapped_column(String(66))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def initialize_database() -> None:
    """Apply explicit versioned migrations; never mutate schema on API startup."""
    from app.config import Settings
    from app.migrations import migrate

    engine = create_engine(Settings().database_url, connect_args={"connect_timeout": 5})
    migrate(engine)
    engine.dispose()


if __name__ == "__main__":
    initialize_database()
