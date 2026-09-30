import hashlib
import json
import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from eth_account import Account
from sqlalchemy import func, select, text

from app.db import Task, User
from app.migrations import migrate, revisions
from app.task_catalog import canonical_json, commitment
from test_auth import client, login


def draft(client, headers, **changes):
    info = client.get("/api/v1/tasks/templates", headers=headers).json()[0]
    return {"title": "Fix access rules", "description": "Deny suspended accounts and viewers.",
            "templateId": info["id"], "repositoryRevision": info["repositoryRevision"],
            "rewardWei": "100000000000000001", **changes}


def create(client, headers, body, key=None):
    return client.post("/api/v1/tasks", headers={**headers, "Idempotency-Key": key or str(uuid.uuid4())}, json=body)


def test_save_read_and_reproduce_commitments(client):
    account = Account.create()
    headers = login(client, account)
    body = draft(client, headers)
    response = create(client, headers, body)
    assert response.status_code == 201, response.text
    task = response.json()
    assert task["status"] == "AWAITING_FUNDING"
    assert task["rewardWei"] == body["rewardWei"]
    assert task["creatorWallet"] == account.address.lower()
    assert task["fundingAvailable"] is False
    assert task["taskHash"] == commitment(task["canonicalPayload"])
    payload = json.loads(task["canonicalPayload"])
    assert canonical_json(payload) == task["canonicalPayload"]
    assert payload["chainId"] == "10143"
    assert payload["verificationPolicyHash"] == commitment(canonical_json(payload["verificationPolicy"]))
    assert client.get(f'/api/v1/tasks/{task["id"]}', headers=headers).json() == task
    with client.app.state.sessions() as db:
        saved = db.get(Task, uuid.UUID(task["id"]))
        assert "sha256:" + hashlib.sha256(saved.repository_snapshot.encode()).hexdigest() == task["repository"]["revision"]


def test_duplicate_retry_and_conflicting_retry(client):
    headers = login(client)
    body = draft(client, headers)
    key = str(uuid.uuid4())
    first = create(client, headers, body, key)
    retry = create(client, headers, body, key)
    assert retry.status_code == 200
    assert first.json() == retry.json()
    conflict = create(client, headers, {**body, "rewardWei": "2"}, key)
    assert conflict.status_code == 409
    with client.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Task)) == 1


def test_owner_only_and_auth_required(client):
    headers = login(client)
    body = draft(client, headers)
    task = create(client, headers, body).json()
    other = login(client)
    assert client.get(f'/api/v1/tasks/{task["id"]}', headers=other).status_code == 404
    assert client.get(f'/api/v1/tasks/{task["id"]}').status_code == 401
    assert client.get("/api/v1/tasks/templates").status_code == 401
    assert create(client, {}, body).status_code == 401


@pytest.mark.parametrize("changes", [
    {"title": " "}, {"title": "a" * 201}, {"description": ""}, {"description": "x" * 10001},
    {"rewardWei": "0"}, {"rewardWei": "-1"}, {"rewardWei": "1.5"}, {"rewardWei": "1e18"},
    {"rewardWei": "01"}, {"rewardWei": 100}, {"rewardWei": str(2**256)},
    {"creatorWallet": "0x" + "1" * 40}, {"status": "PAID"}, {"verificationCommand": "echo pass"},
    {"title": "bad\x00title"}, {"templateId": "https://attacker.example/repo"},
])
def test_reject_invalid_or_client_controlled_fields(client, changes):
    headers = login(client)
    response = create(client, headers, draft(client, headers, **changes))
    assert response.status_code == 422, response.text


def test_stale_revision_rejected(client):
    headers = login(client)
    response = create(client, headers, draft(client, headers, repositoryRevision="sha256:old"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "REPOSITORY_REVISION_CHANGED"


def test_normalization_and_uint256_precision(client):
    headers = login(client)
    maximum = str(2**256 - 1)
    response = create(client, headers, draft(client, headers, title="  Cafe\u0301  ",
                                             description="Line one\r\nLine two", rewardWei=maximum))
    assert response.status_code == 201, response.text
    task = response.json()
    assert task["title"] == "Café"
    assert task["description"] == "Line one\nLine two"
    assert task["rewardWei"] == maximum


def test_migrations_preserve_users_and_are_repeatable(client):
    headers = login(client)
    with client.app.state.sessions() as db:
        before = db.scalar(select(func.count()).select_from(User))
        engine = db.get_bind()
    # Simulate the feature-1 database: auth tables exist, tasks do not.
    Task.__table__.drop(engine)
    migrate(engine)
    migrate(engine)
    with client.app.state.sessions() as db:
        assert db.scalar(select(func.count()).select_from(User)) == before
        assert len(db.scalars(select(revisions.c.revision)).all()) == 3
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert create(client, headers, draft(client, headers)).status_code == 201


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requires PostgreSQL transactions")
def test_concurrent_create_has_one_row(client):
    headers = login(client)
    body = draft(client, headers)
    key = str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(client, headers, body, key), range(2)))
    assert sorted(result.status_code for result in results) == [200, 201]
    assert results[0].json()["id"] == results[1].json()["id"]


def test_delete_preserves_record_and_prevents_replay(client):
    headers = login(client)
    body = draft(client, headers)
    key = str(uuid.uuid4())
    task = create(client, headers, body, key).json()
    url = f'/api/v1/tasks/{task["id"]}'
    assert client.delete(url, headers=headers).status_code == 204
    assert client.delete(url, headers=headers).status_code == 204
    assert client.get(url, headers=headers).status_code == 404
    assert create(client, headers, body, key).status_code == 410
    with client.app.state.sessions() as db:
        saved = db.get(Task, uuid.UUID(task["id"]))
        assert saved.deleted_at is not None
        assert saved.task_hash == task["taskHash"]
        assert saved.canonical_payload == task["canonicalPayload"]
    assert create(client, headers, body).status_code == 201


def test_delete_requires_owner_and_auth(client):
    headers = login(client)
    task = create(client, headers, draft(client, headers)).json()
    url = f'/api/v1/tasks/{task["id"]}'
    assert client.delete(url).status_code == 401
    assert client.delete(url, headers=login(client)).status_code == 404
    assert client.delete(f'/api/v1/tasks/{uuid.uuid4()}', headers=headers).status_code == 404
    assert client.get(url, headers=headers).status_code == 200


@pytest.mark.parametrize("status", ["FUNDED", "RUNNING", "VERIFIED", "PAID", "FAILED"])
def test_delete_rejects_other_states(client, status):
    headers = login(client)
    task = create(client, headers, draft(client, headers)).json()
    # Simulate future lifecycle states in the isolated test database only.
    with client.app.state.sessions() as db:
        if db.bind.dialect.name == "postgresql":
            db.execute(text("ALTER TABLE tasks DROP CONSTRAINT ck_task_initial_status"))
        else:
            db.execute(text("PRAGMA ignore_check_constraints = ON"))
        saved = db.get(Task, uuid.UUID(task["id"]))
        saved.status = status
        db.commit()
    response = client.delete(f'/api/v1/tasks/{task["id"]}', headers=headers)
    assert response.status_code == 409
    with client.app.state.sessions() as db:
        assert db.get(Task, uuid.UUID(task["id"])).deleted_at is None


def test_deletion_migration_preserves_existing_task(client):
    headers = login(client)
    task = create(client, headers, draft(client, headers)).json()
    with client.app.state.sessions() as db:
        engine = db.get_bind()
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE tasks DROP COLUMN deleted_at"))
    migrate(engine)
    migrate(engine)
    assert client.get(f'/api/v1/tasks/{task["id"]}', headers=headers).json() == task
    assert client.delete(f'/api/v1/tasks/{task["id"]}', headers=headers).status_code == 204
