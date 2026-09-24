"""POST/GET /auth/* (PRD §7.2, §8.1)."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    ACCESS_TOKEN_COOKIE,
    CSRF_COOKIE,
    REFRESH_TOKEN_COOKIE,
    csrf_protect,
    enforce_login_rate_limit,
    get_current_user,
    get_db,
    request_id_of,
)
from app.api.schemas import ChangePasswordRequest, LoginRequest, MeResponse
from app.config.settings import get_settings
from app.database.models import RefreshToken, User
from app.database.scoping import caregiver_subject_ids
from app.monitoring.audit import log_audit
from app.security.passwords import hash_password, verify_password
from app.security.tokens import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_kwargs() -> dict:
    settings = get_settings()
    return {"httponly": True, "secure": settings.is_production, "samesite": "lax"}


def _set_session_cookies(response: Response, user: User, db: Session) -> None:
    settings = get_settings()
    access_token = create_access_token(user.id, user.role, settings.jwt_secret)

    refresh_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_token_expiry(),
        )
    )

    csrf_token = secrets.token_urlsafe(32)

    response.set_cookie(ACCESS_TOKEN_COOKIE, access_token, max_age=15 * 60, **_cookie_kwargs())
    response.set_cookie(
        REFRESH_TOKEN_COOKIE, refresh_token, max_age=7 * 24 * 3600, **_cookie_kwargs()
    )
    # CSRF cookie must be readable by client JS for the double-submit pattern.
    response.set_cookie(
        CSRF_COOKIE, csrf_token, max_age=7 * 24 * 3600, httponly=False,
        secure=settings.is_production, samesite="lax",
    )


def _clear_session_cookies(response: Response) -> None:
    for name in (ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name)


def _user_summary(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role,
            "must_change_password": user.must_change_password}


@router.post("/login")
def login(
    body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> dict:
    enforce_login_rate_limit(request, body.email)

    user = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        if user is not None:
            log_audit(db, action="login", result="failure", user_id=user.id,
                       request_id=request_id_of(request))
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")

    if user.status != "active":
        log_audit(db, action="login", result="failure", user_id=user.id,
                   request_id=request_id_of(request))
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="account_disabled")

    user.last_login_at = datetime.now(timezone.utc)
    _set_session_cookies(response, user, db)
    log_audit(db, action="login", result="success", user_id=user.id,
               request_id=request_id_of(request))
    db.commit()
    return _user_summary(user)


@router.post("/refresh", dependencies=[Depends(csrf_protect)])
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    presented = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not presented:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")

    token_hash = hash_refresh_token(presented)
    row = db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_refresh_token")

    if row.revoked_at is not None:
        # Reuse of an already-rotated token: assume compromise, kill the family.
        stale_tokens = db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None)
            )
        ).scalars()
        now = datetime.now(timezone.utc)
        for token in stale_tokens:
            token.revoked_at = now
        log_audit(db, action="refresh_reuse_detected", result="failure", user_id=row.user_id,
                   request_id=request_id_of(request))
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="reuse_detected")

    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="expired")

    user = db.get(User, row.user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")

    new_refresh_token = generate_refresh_token()
    new_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(new_refresh_token),
        expires_at=refresh_token_expiry(),
    )
    db.add(new_row)
    db.flush()
    row.revoked_at = datetime.now(timezone.utc)
    row.replaced_by = new_row.id

    access_token = create_access_token(user.id, user.role, get_settings().jwt_secret)
    response.set_cookie(ACCESS_TOKEN_COOKIE, access_token, max_age=15 * 60, **_cookie_kwargs())
    response.set_cookie(
        REFRESH_TOKEN_COOKIE, new_refresh_token, max_age=7 * 24 * 3600, **_cookie_kwargs()
    )
    db.commit()
    return _user_summary(user)


@router.post("/logout", dependencies=[Depends(csrf_protect)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    presented = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if presented:
        token_hash = hash_refresh_token(presented)
        row = db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).scalar_one_or_none()
        if row is not None and row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)
            log_audit(db, action="logout", result="success", user_id=row.user_id,
                       request_id=request_id_of(request))
            db.commit()
    _clear_session_cookies(response)
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    assigned = (
        sorted(caregiver_subject_ids(db, current_user.id))
        if current_user.role == "caregiver"
        else []
    )
    return MeResponse(
        id=current_user.id, name=current_user.name, email=current_user.email,
        role=current_user.role, must_change_password=current_user.must_change_password,
        assigned_subject_ids=assigned,
    )


@router.post("/change-password", dependencies=[Depends(csrf_protect)])
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="incorrect_password")

    current_user.password_hash = hash_password(body.new_password)
    current_user.must_change_password = False
    log_audit(db, action="change_password", result="success", user_id=current_user.id,
               request_id=request_id_of(request))
    db.commit()
    return {"status": "ok"}
