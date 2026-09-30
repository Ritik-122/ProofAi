"""Small ordered migration runner for the MVP. Applied revisions are immutable."""
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, MetaData, Numeric, String, Table, Text, UniqueConstraint, Uuid, select, text

# Frozen initial definitions: future model edits must not rewrite historical migrations.
schema = MetaData()
users_v1 = Table("users", schema,
    Column("id", Uuid, primary_key=True), Column("wallet_address", String(42), nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False), Column("challenge_id", Uuid),
    Column("challenge_message", String(1200)), Column("challenge_issued_at", DateTime(timezone=True)),
    Column("challenge_expires_at", DateTime(timezone=True)))
sessions_v1 = Table("auth_sessions", schema,
    Column("id", Uuid, primary_key=True), Column("user_id", ForeignKey("users.id"), nullable=False, index=True),
    Column("expires_at", DateTime(timezone=True), nullable=False, index=True))
tasks_v1 = Table("tasks", schema,
    Column("id", Uuid, primary_key=True), Column("creator_id", ForeignKey("users.id"), nullable=False, index=True),
    Column("request_id", Uuid, nullable=False), Column("request_payload", Text, nullable=False),
    Column("title", String(200), nullable=False), Column("description", Text, nullable=False),
    Column("template_id", String(80), nullable=False), Column("repository_revision", String(80), nullable=False),
    Column("repository_snapshot", Text, nullable=False),
    Column("reward_wei", Numeric(78, 0).with_variant(String(78), "sqlite"), nullable=False),
    Column("status", String(40), nullable=False), Column("canonical_payload", Text, nullable=False),
    Column("task_hash", String(66), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("creator_id", "request_id", name="uq_task_creator_request"),
    CheckConstraint("reward_wei > 0", name="ck_task_positive_reward"),
    CheckConstraint("status = 'AWAITING_FUNDING'", name="ck_task_initial_status"))

revisions = Table("schema_migrations", MetaData(), Column("revision", String(40), primary_key=True),
                  Column("applied_at", DateTime(timezone=True), nullable=False))


def migrate(engine):
    with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(781456201)"))
        revisions.create(connection, checkfirst=True)
        applied = set(connection.scalars(select(revisions.c.revision)))
        for revision, tables in (("001_wallet_auth", (users_v1, sessions_v1)),
                                 ("002_task_creation", (tasks_v1,))):
            if revision in applied:
                continue
            # Baseline adoption preserves existing feature-1 tables and sessions.
            for table in tables:
                table.create(connection, checkfirst=True)
            connection.execute(revisions.insert().values(revision=revision, applied_at=datetime.now(timezone.utc)))
        if "003_task_deletion" not in applied:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE"))
            connection.execute(revisions.insert().values(revision="003_task_deletion", applied_at=datetime.now(timezone.utc)))
