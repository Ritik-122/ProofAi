import json
import unicodedata
import uuid

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth import AuthError, current_session, database, iso, utcnow
from app.db import AuthSession, Task, User
from app.task_catalog import TEMPLATE_ID, canonical_json, commitment, template

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTask(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    templateId: str = Field(min_length=1, max_length=80)
    repositoryRevision: str = Field(min_length=1, max_length=80)
    rewardWei: str = Field(pattern=r"^[1-9][0-9]{0,77}$")

    @field_validator("title", "description", mode="before")
    @classmethod
    def normalize_text(cls, value):
        if isinstance(value, str):
            value = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n")).strip()
            if any(unicodedata.category(char) in {"Cs", "Cc"} and char not in "\n\t" for char in value):
                raise ValueError("Control characters are not allowed")
        return value

    @field_validator("rewardWei")
    @classmethod
    def valid_reward(cls, value):
        if int(value) > 2**256 - 1:
            raise ValueError("Reward exceeds uint256")
        return value


def describe(task: Task) -> dict:
    payload = json.loads(task.canonical_payload)
    return {"id": str(task.id), "title": task.title, "description": task.description,
            "rewardWei": str(task.reward_wei), "status": task.status, "taskHash": task.task_hash,
            "createdAt": iso(task.created_at), "creatorWallet": payload["creator"],
            "repository": payload["repository"], "verificationPolicy": payload["verificationPolicy"],
            "chainId": payload["chainId"], "canonicalPayload": task.canonical_payload,
            "fundingAvailable": False}


@router.get("/templates")
def templates(auth: tuple[User, AuthSession] = Depends(current_session)):
    info, _ = template()
    return [info]


@router.post("", status_code=201)
def create_task(body: CreateTask, request: Request, response: Response,
                idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
                auth: tuple[User, AuthSession] = Depends(current_session), db: Session = Depends(database)):
    user, _ = auth
    request_payload = canonical_json(body.model_dump())
    existing = db.scalar(select(Task).where(Task.creator_id == user.id, Task.request_id == idempotency_key))
    if existing:
        return replay(existing, request_payload, response)
    if body.templateId != TEMPLATE_ID:
        raise AuthError("REPOSITORY_NOT_SUPPORTED", "Select a supported demo repository.", 422)
    info, snapshot = template()
    if body.repositoryRevision != info["repositoryRevision"]:
        raise AuthError("REPOSITORY_REVISION_CHANGED", "The demo was updated. Refresh the form before creating a task.", 409)
    task_id = uuid.uuid4()
    payload = {
        "version": 1, "domain": "proofai.task-metadata", "taskId": str(task_id),
        "creator": user.wallet_address, "chainId": str(request.app.state.config.chain_id),
        "title": body.title, "description": body.description, "rewardWei": body.rewardWei,
        "repository": {"id": info["id"], "url": info["repositoryUrl"], "revision": info["repositoryRevision"]},
        "verificationPolicy": info["verificationPolicy"], "verificationPolicyHash": info["verificationPolicyHash"],
    }
    canonical = canonical_json(payload)
    # Unique (creator, request) protects simultaneous retries without a process-local lock.
    stmt = insert(Task).values(id=task_id, creator_id=user.id, request_id=idempotency_key,
        request_payload=request_payload, title=body.title, description=body.description,
        template_id=info["id"], repository_revision=info["repositoryRevision"], repository_snapshot=snapshot,
        reward_wei=body.rewardWei, status="AWAITING_FUNDING", canonical_payload=canonical,
        task_hash=commitment(canonical), created_at=utcnow()).on_conflict_do_nothing(
            index_elements=[Task.creator_id, Task.request_id]).returning(Task.id)
    inserted = db.scalar(stmt)
    if inserted is None:
        existing = db.scalar(select(Task).where(Task.creator_id == user.id, Task.request_id == idempotency_key))
        return replay(existing, request_payload, response)
    db.commit()
    return describe(db.get(Task, inserted))


def replay(task: Task, payload: str, response: Response):
    if task.deleted_at is not None:
        raise AuthError("TASK_DELETED", "This task was deleted. Create a new task with a new request key.", 410)
    if task.request_payload != payload:
        raise AuthError("IDEMPOTENCY_CONFLICT", "This request key was already used for different task details.", 409)
    response.status_code = 200
    return describe(task)


@router.get("/{task_id}")
def get_task(task_id: uuid.UUID, auth: tuple[User, AuthSession] = Depends(current_session),
             db: Session = Depends(database)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.creator_id == auth[0].id, Task.deleted_at.is_(None)))
    if task is None:
        raise AuthError("TASK_NOT_FOUND", "This task was not found for your wallet.", 404)
    return describe(task)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: uuid.UUID, auth: tuple[User, AuthSession] = Depends(current_session),
                db: Session = Depends(database)):
    # The status guard is part of the write, so a concurrent state transition
    # cannot leave a funded task deleted. Future funding must also guard deleted_at.
    deleted = db.scalar(update(Task).where(
        Task.id == task_id, Task.creator_id == auth[0].id,
        Task.status == "AWAITING_FUNDING", Task.deleted_at.is_(None),
    ).values(deleted_at=utcnow()).returning(Task.id))
    if deleted is not None:
        db.commit()
        return Response(status_code=204)
    task = db.scalar(select(Task).where(Task.id == task_id, Task.creator_id == auth[0].id))
    if task is None:
        raise AuthError("TASK_NOT_FOUND", "This task was not found for your wallet.", 404)
    if task.deleted_at is not None:
        return Response(status_code=204)
    raise AuthError("TASK_NOT_DELETABLE", "Only tasks awaiting funding can be deleted.", 409)
