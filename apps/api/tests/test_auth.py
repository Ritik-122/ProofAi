import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import jwt
import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text, update
from sqlalchemy.pool import StaticPool

from app.auth import utcnow
from app.config import Settings
from app.db import Base, User
from app.main import create_app


@pytest.fixture
def client():
    url = os.getenv("TEST_DATABASE_URL")
    schema = "proofai_test_" + uuid.uuid4().hex
    admin = None
    if url:
        admin = create_engine(url)
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        # Fast tests only. Runtime configuration explicitly requires PostgreSQL.
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    config = Settings(database_url="postgresql+psycopg://test:test@localhost/test",
                      jwt_secret="unit-test-only-" + "a" * 48, _env_file=None)
    Base.metadata.create_all(engine)
    app = create_app(config, engine)
    with TestClient(app) as test_client:
        yield test_client
    if admin:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def challenge(client, account):
    response = client.post("/api/v1/auth/nonce", json={"walletAddress": account.address})
    assert response.status_code == 200, response.text
    return response.json()


def proof(account, data):
    signature = Account.sign_message(encode_defunct(text=data["message"]), account.key).signature
    return {"walletAddress": account.address, "challengeId": data["challengeId"],
            "signature": "0x" + signature.hex()}


def login(client, account=None):
    account = account or Account.create()
    response = client.post("/api/v1/auth/verify", json=proof(account, challenge(client, account)))
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["accessToken"]}


def test_signed_login_and_logout(client):
    account = Account.create()
    headers = login(client, account)
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["walletAddress"] == account.address
    assert response.json()["chainId"] == 10143
    assert response.headers["cache-control"] == "no-store"
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_signature_cannot_be_replayed(client):
    account = Account.create()
    body = proof(account, challenge(client, account))
    assert client.post("/api/v1/auth/verify", json=body).status_code == 200
    assert client.post("/api/v1/auth/verify", json=body).status_code == 401


def test_wrong_signer_rejected_without_consuming_challenge(client):
    account = Account.create()
    data = challenge(client, account)
    forged = proof(Account.create(), data)
    forged["walletAddress"] = account.address
    assert client.post("/api/v1/auth/verify", json=forged).status_code == 401
    assert client.post("/api/v1/auth/verify", json=proof(account, data)).status_code == 200


def test_expired_challenge(client):
    account = Account.create()
    data = challenge(client, account)
    with client.app.state.sessions.begin() as db:
        db.execute(update(User).values(challenge_expires_at=utcnow() - timedelta(seconds=1)))
    assert client.post("/api/v1/auth/verify", json=proof(account, data)).status_code == 401


def test_new_challenge_invalidates_old(client):
    account = Account.create()
    old = challenge(client, account)
    with client.app.state.sessions.begin() as db:
        db.execute(update(User).values(challenge_issued_at=utcnow() - timedelta(seconds=10)))
    new = challenge(client, account)
    assert old["message"] != new["message"]
    assert client.post("/api/v1/auth/verify", json=proof(account, old)).status_code == 401
    assert client.post("/api/v1/auth/verify", json=proof(account, new)).status_code == 200


def test_nonce_is_bound_to_server_origin_chain_and_expiry(client):
    data = challenge(client, Account.create())
    assert data["message"].startswith("localhost:5173 wants you to sign in")
    assert "URI: http://localhost:5173" in data["message"]
    assert "Chain ID: 10143" in data["message"]
    assert "Expiration Time:" in data["message"]
    assert client.post("/api/v1/auth/nonce", json={"walletAddress": Account.create().address},
                       headers={"Origin": "https://attacker.example"}).status_code == 403


def test_tampered_message_cannot_authenticate(client):
    account = Account.create()
    data = challenge(client, account)
    data["message"] = data["message"].replace("Chain ID: 10143", "Chain ID: 1")
    assert client.post("/api/v1/auth/verify", json=proof(account, data)).status_code == 401


def test_address_normalization_and_nonce_cooldown(client):
    account = Account.create()
    challenge(client, account)
    response = client.post("/api/v1/auth/nonce", json={"walletAddress": account.address.lower()})
    assert response.status_code == 429
    with client.app.state.sessions() as db:
        users = db.scalars(select(User)).all()
        assert len(users) == 1
        assert users[0].wallet_address == account.address.lower()


@pytest.mark.parametrize("change", ["expired", "wrong-audience", "wrong-chain", "wrong-key", "missing-exp"])
def test_invalid_tokens(client, change):
    headers = login(client)
    config = client.app.state.config
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = jwt.decode(token, options={"verify_signature": False})
    key = config.jwt_secret
    if change == "expired":
        payload["exp"] = 1
    elif change == "wrong-audience":
        payload["aud"] = "https://other.example"
    elif change == "wrong-chain":
        payload["chainId"] = 1
    elif change == "wrong-key":
        key = "b" * 48
    else:
        del payload["exp"]
    forged = jwt.encode(payload, key, algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_protected_endpoint_and_input_validation(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/nonce", json={"walletAddress": "bad"}).status_code == 422
    response = client.post("/api/v1/auth/verify", json={"walletAddress": Account.create().address,
                                                      "challengeId": str(uuid.uuid4()), "signature": "0x00"})
    assert response.status_code == 422
    assert "requestId" in response.json()["error"]


@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requires real PostgreSQL transactions")
def test_concurrent_signature_replay_has_only_one_winner(client):
    account = Account.create()
    body = proof(account, challenge(client, account))
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: client.post("/api/v1/auth/verify", json=body).status_code, range(2)))
    assert sorted(statuses) == [200, 401]
