"""Auth/role logic ported verbatim from dashboard/app.py (lines 96-194),
behind a get_current_user() FastAPI dependency so a real auth provider
(JWT/OAuth/session) can replace it later without touching any caller.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional

import pandas as pd
import yaml
from fastapi import Header, HTTPException

CONFIG_PATH = "config.yaml"


def _load_config() -> dict:
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def get_auth_config() -> dict:
    return _load_config().get("auth", {"enabled": False, "users": []})


def _auth_secret() -> str:
    auth = _load_config().get("auth", {})
    return auth.get("jwt_secret") or auth.get("secret_key", "fallback-secret-key-change-me")


def validate_token(token: str, secret: str) -> Optional[dict]:
    try:
        payload, sig = token.rsplit(":", 1)
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        username, role, ts = payload.split(":", 2)
        if time.time() - int(ts) > 86400:
            return None
        for u in get_auth_config().get("users", []):
            if u.get("username") == username:
                return {"username": username, "role": role, "display_name": u.get("display_name", username)}
        return {"username": username, "role": role, "display_name": username}
    except Exception:
        return None


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    """Same default as dashboard.app.get_current_user: with auth disabled (the
    shipped config.yaml.example default, no `auth:` section) everyone is
    guest/admin. If auth is enabled, expects `Authorization: Bearer <token>`."""
    auth_config = get_auth_config()
    if not auth_config.get("enabled", False):
        return {"username": "guest", "role": "admin", "display_name": "Guest User"}
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    user = validate_token(token, _auth_secret())
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def get_user_permissions(user: dict) -> dict:
    role = user.get("role", "viewer")
    if role == "admin":
        return {"can_acknowledge": True, "can_dismiss": True, "can_escalate": True,
                "can_export": True, "can_view_all": True, "can_manage_settings": True}
    if role == "caregiver":
        return {"can_acknowledge": True, "can_dismiss": False, "can_escalate": True,
                "can_export": True, "can_view_all": False, "can_manage_settings": False}
    if role == "viewer":
        return {"can_acknowledge": False, "can_dismiss": False, "can_escalate": False,
                "can_export": False, "can_view_all": False, "can_manage_settings": False}
    return {"can_acknowledge": False, "can_dismiss": False, "can_escalate": False,
            "can_export": False, "can_view_all": False, "can_manage_settings": False}


def filter_by_role(df: pd.DataFrame, user: dict) -> pd.DataFrame:
    """admin sees all alerts; caregiver/viewer see only their assigned subjects
    (auth.role_permissions[role] in config.yaml, default S1/S2/S3)."""
    if user.get("role") == "admin" or get_user_permissions(user).get("can_view_all"):
        return df
    allowed = set(get_auth_config().get("role_permissions", {}).get(user.get("role", ""), ["S1", "S2", "S3"]))
    return df[df["subject_id"].isin(allowed)]
