import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import jwt
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_keys.exceptions import BadSignature
from eth_utils import to_checksum_address
from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import AuthSession, User

router = APIRouter(prefix="/auth", tags=["authentication"])
bearer = HTTPBearer(auto_error=False)


class AuthError(Exception):
    def __init__(self, code: str, message: str, status: int = 401):
        self.code, self.message, self.status = code, message, status


class NonceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    walletAddress: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")


class VerifyRequest(NonceRequest):
    challengeId: uuid.UUID
    signature: str = Field(pattern=r"^0x[0-9a-fA-F]{130}$")


def database(request: Request):
    with request.app.state.sessions() as session:
        yield session


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


@router.post("/nonce")
def nonce(body: NonceRequest, request: Request, db: Session = Depends(database)):
    config = request.app.state.config
    now = utcnow()
    expires = now + timedelta(seconds=config.challenge_ttl_seconds)
    challenge_id = uuid.uuid4()
    address = body.walletAddress.lower()
    # SIWE-shaped EIP-191 message. Server owns every field; client cannot replace it.
    message = (
        f"{urlsplit(config.app_origin).netloc} wants you to sign in with your Ethereum account:\n"
        f"{to_checksum_address(address)}\n\n"
        "Sign in to ProofAI. This does not authorize a transaction or transfer funds.\n\n"
        f"URI: {config.app_origin}\nVersion: 1\nChain ID: {config.chain_id}\n"
        f"Nonce: {secrets.token_hex(16)}\nIssued At: {iso(now)}\n"
        f"Expiration Time: {iso(expires)}\nRequest ID: {challenge_id}"
    )
    values = dict(challenge_id=challenge_id, challenge_message=message,
                  challenge_issued_at=now, challenge_expires_at=expires)
    stmt = insert(User).values(id=uuid.uuid4(), wallet_address=address, created_at=now, **values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[User.wallet_address], set_=values,
        where=or_(User.challenge_issued_at.is_(None),
                  User.challenge_issued_at <= now - timedelta(seconds=config.nonce_cooldown_seconds)),
    ).returning(User.id)
    if db.scalar(stmt) is None:
        db.rollback()
        raise AuthError("TOO_MANY_REQUESTS", "Wait a few seconds before requesting another signature.", 429)
    db.commit()
    return {"challengeId": str(challenge_id), "message": message, "expiresAt": iso(expires),
            "chainId": config.chain_id}


@router.post("/verify")
def verify(body: VerifyRequest, request: Request, db: Session = Depends(database)):
    config = request.app.state.config
    address = body.walletAddress.lower()
    user = db.scalar(select(User).where(User.wallet_address == address,
                                       User.challenge_id == body.challengeId))
    if user is None or user.challenge_message is None:
        raise AuthError("INVALID_CHALLENGE", "Request a new sign-in message.")
    try:
        recovered = Account.recover_message(encode_defunct(text=user.challenge_message), signature=body.signature)
    except (ValueError, TypeError, OverflowError, BadSignature):
        raise AuthError("INVALID_SIGNATURE", "The wallet signature is invalid.") from None
    if recovered.lower() != address:
        raise AuthError("INVALID_SIGNATURE", "The signature does not match this wallet.")
    now = utcnow()
    # Atomic compare-and-consume: concurrent requests cannot reuse the same challenge.
    consumed = db.execute(update(User).where(
        User.id == user.id, User.challenge_id == body.challengeId,
        User.challenge_expires_at > now,
    ).values(challenge_id=None, challenge_message=None, challenge_expires_at=None)
      .execution_options(synchronize_session=False))
    if consumed.rowcount != 1:
        db.rollback()
        raise AuthError("INVALID_CHALLENGE", "This sign-in message has expired or was already used.")
    expires = now + timedelta(seconds=config.token_ttl_seconds)
    auth_session = AuthSession(id=uuid.uuid4(), user_id=user.id, expires_at=expires)
    db.add(auth_session)
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    token = jwt.encode({"sub": str(user.id), "jti": str(auth_session.id),
                        "iat": now, "exp": expires, "iss": "proofai-api",
                        "aud": config.app_origin, "chainId": config.chain_id},
                       config.jwt_secret, algorithm="HS256")
    db.commit()
    return {"accessToken": token, "tokenType": "bearer", "expiresAt": iso(expires)}


def current_session(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                    db: Session = Depends(database)) -> tuple[User, AuthSession]:
    if credentials is None:
        raise AuthError("UNAUTHENTICATED", "Sign in with your wallet to continue.")
    config = request.app.state.config
    try:
        payload = jwt.decode(credentials.credentials, config.jwt_secret, algorithms=["HS256"],
                             audience=config.app_origin, issuer="proofai-api",
                             options={"require": ["sub", "jti", "iat", "exp", "iss", "aud", "chainId"]})
        session_id, user_id = uuid.UUID(payload["jti"]), uuid.UUID(payload["sub"])
        if payload["chainId"] != config.chain_id:
            raise ValueError("Wrong chain")
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise AuthError("UNAUTHENTICATED", "Your session has expired. Please sign in again.") from None
    row = db.execute(select(User, AuthSession).join(AuthSession, AuthSession.user_id == User.id).where(
        User.id == user_id, AuthSession.id == session_id, AuthSession.expires_at > utcnow(),
    )).first()
    if row is None:
        raise AuthError("UNAUTHENTICATED", "Your session is no longer active.")
    return row[0], row[1]


@router.get("/me")
def me(request: Request, auth: tuple[User, AuthSession] = Depends(current_session)):
    user, session = auth
    return {"id": str(user.id), "walletAddress": to_checksum_address(user.wallet_address),
            "chainId": request.app.state.config.chain_id, "expiresAt": iso(session.expires_at)}


@router.post("/logout", status_code=204)
def logout(auth: tuple[User, AuthSession] = Depends(current_session), db: Session = Depends(database)):
    db.delete(auth[1])
    db.commit()
