"""VS-03 — dev identity stub.

Real auth (managed provider) is a later epic. For the slice we resolve a single
dev user from a static token so every request is scoped to a user_id.
"""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.identity.models import User

DEV_TOKEN = "dev-token"
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"


def get_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User:
    token = (authorization or "").removeprefix("Bearer ").strip()
    if token != DEV_TOKEN:
        raise HTTPException(status_code=401, detail="invalid dev token")
    user = session.get(User, DEV_USER_ID)
    if user is None:  # auto-provision the dev user
        user = User(id=DEV_USER_ID, auth_ref="dev", region="EU")
        session.add(user)
        session.commit()
    return user
