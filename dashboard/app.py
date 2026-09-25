"""
Dashboard Module
----------------
Fall Detection System for Elderly Care — caregiver-first safety operations
console built on Streamlit with custom status surfaces, a privacy-forward
visual system, and native alert/live workflows.
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Streamlit only adds the script's own directory (dashboard/) to sys.path,
# so resolve the project root eagerly to import project modules reliably.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import json
import time
import hashlib
import hmac
import html
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import Optional
import logging

from alert_store import AlertStore
from project_config import PROJECT_ROOT, load_config, resolve_path, validate_config

logger = logging.getLogger(__name__)

ALERT_LOG = resolve_path("logs/alerts.jsonl", base=PROJECT_ROOT)

# ─── Midnight Safety Operations theme tokens ─────────────────────────────────
_BG = "#0b1220"
_SURFACE = "#111c2e"
_BORDER = "#243b53"
_TEXT = "#f4f7fb"
_SUB = "#9fb3c8"
_MUTED = "#71869c"
_PRIMARY = "#5eead4"
_GREEN = "#34d399"
_AMBER = "#fbbf24"
_RED = "#fb7185"

# ═══════════════════════════════════════════════════════════════════════════════
# LIGHT THEME CSS  (minimal: spacing, typography, and the few custom surfaces)
# ═══════════════════════════════════════════════════════════════════════════════

THEME_CSS = f"""
<style>
.stApp {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif !important;
    color: {_TEXT};
}}
section[data-testid="stSidebar"] {{
    background: {_SURFACE} !important;
    border-right: 1px solid {_BORDER} !important;
}}
section[data-testid="stSidebar"] .stAppNavHeader {{
    padding: 0.5rem 0 0.25rem;
}}
.main .block-container {{
    padding-top: 1.2rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1180px !important;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.5rem;
    font-weight: 650;
}}
[data-testid="stMetricLabel"] {{
    color: {_SUB};
    font-weight: 500;
}}
[data-testid="stExpanderBorder"] {{
    border-color: {_BORDER} !important;
}}
h1, h2, h3 {{
    letter-spacing: -0.01em;
}}
code, [data-testid="stToolbarButton"] {{
    font-size: 0.85rem;
}}
/* Caregiver-first visual system: calm surfaces, clear hierarchy, generous targets. */
[data-testid="stMetric"] {{
    background: {_SURFACE};
    border: 1px solid {_BORDER};
    border-radius: 14px;
    padding: 0.9rem 1rem;
    min-height: 92px;
}}
[data-testid="stDataFrame"] {{
    border: 1px solid {_BORDER};
    border-radius: 12px;
    overflow: hidden;
}}
[data-testid="stButton"] button {{
    min-height: 42px;
    border-radius: 10px;
    font-weight: 600;
}}
button:focus-visible, a:focus-visible, input:focus-visible {{
    outline: 3px solid rgba(15, 118, 110, 0.35) !important;
    outline-offset: 2px !important;
}}
@media (max-width: 720px) {{
    .main .block-container {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
    h1 {{ font-size: 1.8rem !important; }}
}}
/* ── Product surfaces ───────────────────────────────────────────────────── */
:root {{
    --fg-ink: #102a43;
    --fg-muted: #627d98;
    --fg-soft: #f0f4f8;
    --fg-teal: #0f766e;
    --fg-navy: #102a43;
    --fg-radius: 18px;
}}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
.stApp {{
    background:
        radial-gradient(circle at 85% -10%, rgba(20, 184, 166, 0.08), transparent 32rem),
        linear-gradient(180deg, #f8fbfd 0%, #f3f7fa 100%);
}}
.main .block-container {{ max-width: 1440px !important; padding-top: 1.6rem !important; }}
section[data-testid="stSidebar"] {{ width: 252px !important; }}
section[data-testid="stSidebar"] [data-testid="stNav"] {{ padding-top: 0.45rem; }}
section[data-testid="stSidebar"] [data-testid="stNavLink"] {{
    border-radius: 11px;
    margin: 0.18rem 0;
    padding: 0.55rem 0.7rem;
    color: #486581;
    font-weight: 600;
}}
section[data-testid="stSidebar"] [data-testid="stNavLink"]:hover {{
    background: #e8f5f3;
    color: #0f766e;
}}
section[data-testid="stSidebar"] [aria-current="page"] {{
    background: #dff3ef !important;
    color: #0f766e !important;
}}
.fg-eyebrow {{
    color: #829ab1;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}}
.fg-page-title {{
    color: #102a43;
    font-size: clamp(1.75rem, 3vw, 2.55rem);
    font-weight: 760;
    letter-spacing: -0.045em;
    line-height: 1.05;
    margin: 0.18rem 0 0.42rem;
}}
.fg-page-subtitle {{
    color: #627d98;
    font-size: 0.98rem;
    margin: 0 0 1.25rem;
}}
.fg-topbar {{
    align-items: center;
    background: rgba(255,255,255,0.88);
    border: 1px solid #d9e2ec;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(16,42,67,0.05);
    display: flex;
    justify-content: space-between;
    margin: 0 0 1.35rem;
    padding: 0.78rem 1rem;
}}
.fg-brand {{
    align-items: center;
    color: #102a43;
    display: flex;
    font-size: 0.92rem;
    font-weight: 800;
    gap: 0.58rem;
}}
.fg-brand-mark {{
    align-items: center;
    background: #102a43;
    border-radius: 10px;
    color: #5eead4;
    display: inline-flex;
    font-size: 1rem;
    height: 30px;
    justify-content: center;
    width: 30px;
}}
.fg-topbar-meta {{ color: #627d98; font-size: 0.78rem; font-weight: 600; }}
.fg-status-dot {{
    border-radius: 999px;
    display: inline-block;
    height: 8px;
    margin-right: 0.38rem;
    width: 8px;
}}
.fg-status-strip {{
    display: grid;
    gap: 0.75rem;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin: 0.2rem 0 1.4rem;
}}
.fg-stat-card {{
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: var(--fg-radius);
    box-shadow: 0 8px 24px rgba(16,42,67,0.045);
    min-height: 112px;
    padding: 1rem 1.1rem;
}}
.fg-stat-label {{ color: #627d98; font-size: 0.72rem; font-weight: 750; letter-spacing: 0.08em; text-transform: uppercase; }}
.fg-stat-value {{ color: #102a43; font-size: 1.65rem; font-weight: 780; letter-spacing: -0.04em; margin-top: 0.42rem; }}
.fg-stat-note {{ color: #829ab1; font-size: 0.76rem; margin-top: 0.22rem; }}
.fg-stat-card.fg-attention {{ border-color: #f5c26b; background: #fffaf0; }}
.fg-stat-card.fg-urgent {{ border-color: #ef9a9a; background: #fff7f7; }}
.fg-stat-card.fg-healthy {{ border-color: #9bd8cb; background: #f5fffc; }}
.fg-badge {{
    border-radius: 999px;
    display: inline-flex;
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    padding: 0.3rem 0.58rem;
    text-transform: uppercase;
}}
.fg-badge-green {{ background: #dff7ee; color: #087f5b; }}
.fg-badge-amber {{ background: #fff0c7; color: #a15c00; }}
.fg-badge-red {{ background: #ffe0e0; color: #b42318; }}
.fg-badge-blue {{ background: #e4f0ff; color: #175cd3; }}
.fg-badge-gray {{ background: #e9eff5; color: #486581; }}
.fg-panel {{
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: var(--fg-radius);
    box-shadow: 0 8px 24px rgba(16,42,67,0.045);
    padding: 1.15rem 1.2rem;
}}
.fg-panel-dark {{
    background: #102a43;
    border: 1px solid #243b53;
    border-radius: var(--fg-radius);
    color: #f0f4f8;
    padding: 1.1rem 1.2rem;
}}
.fg-panel-title {{ color: #102a43; font-size: 1.02rem; font-weight: 800; margin-bottom: 0.65rem; }}
.fg-panel-dark .fg-panel-title {{ color: #f0f4f8; }}
.fg-panel-copy {{ color: #627d98; font-size: 0.82rem; line-height: 1.55; }}
.fg-queue-row {{
    align-items: center;
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 15px;
    display: flex;
    gap: 0.8rem;
    justify-content: space-between;
    margin: 0.55rem 0;
    padding: 0.8rem 0.9rem;
}}
.fg-queue-row:hover {{ border-color: #8acfc3; box-shadow: 0 6px 18px rgba(15,118,110,0.08); }}
.fg-queue-main {{ min-width: 0; }}
.fg-queue-subject {{ color: #102a43; font-size: 0.95rem; font-weight: 800; }}
.fg-queue-meta {{ color: #829ab1; font-size: 0.74rem; margin-top: 0.22rem; }}
.fg-queue-right {{ align-items: flex-end; display: flex; flex-direction: column; gap: 0.35rem; }}
.fg-privacy-banner {{
    align-items: flex-start;
    background: #e8f7f4;
    border: 1px solid #b7e5dc;
    border-radius: 14px;
    color: #17665c;
    display: flex;
    font-size: 0.8rem;
    gap: 0.55rem;
    line-height: 1.45;
    padding: 0.78rem 0.9rem;
}}
.fg-live-frame {{
    background: #081421;
    border: 1px solid #243b53;
    border-radius: 18px;
    box-shadow: 0 16px 40px rgba(8,20,33,0.22);
    overflow: hidden;
}}
.fg-live-frame img {{ display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: contain; }}
.fg-live-label {{
    align-items: center;
    background: rgba(8,20,33,0.82);
    border: 1px solid rgba(94,234,212,0.35);
    border-radius: 999px;
    color: #5eead4;
    display: inline-flex;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.68rem;
    font-weight: 800;
    gap: 0.42rem;
    left: 0.9rem;
    letter-spacing: 0.1em;
    padding: 0.42rem 0.68rem;
    position: absolute;
    top: 0.9rem;
}}
.fg-live-wrap {{ position: relative; }}
.fg-kicker-row {{ align-items: center; display: flex; justify-content: space-between; margin-bottom: 0.55rem; }}
.fg-subtle {{ color: #829ab1; font-size: 0.76rem; }}
.fg-health-row {{ align-items: center; border-bottom: 1px solid #edf2f7; display: flex; justify-content: space-between; padding: 0.62rem 0; }}
.fg-health-row:last-child {{ border-bottom: 0; }}
.fg-health-label {{ color: #627d98; font-size: 0.82rem; }}
.fg-health-value {{ color: #102a43; font-size: 0.82rem; font-weight: 750; text-align: right; }}
@media (max-width: 760px) {{
    .fg-status-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .fg-topbar {{ align-items: flex-start; flex-direction: column; gap: 0.5rem; }}
    .fg-queue-row {{ align-items: flex-start; flex-direction: column; }}
    .fg-queue-right {{ align-items: flex-start; flex-direction: row; flex-wrap: wrap; }}
}}
/* ── Midnight Safety Operations overrides ───────────────────────────────── */
:root {{
    --fg-ink: #f4f7fb;
    --fg-muted: #9fb3c8;
    --fg-soft: #16263b;
    --fg-teal: #5eead4;
    --fg-navy: #0b1220;
    --fg-radius: 16px;
}}
.stApp, .stApp [data-testid="stAppViewContainer"] {{
    background: #0b1220 !important;
    color: #f4f7fb !important;
}}
.stApp [data-testid="stHeader"] {{ background: transparent !important; }}
.main .block-container {{
    background: linear-gradient(180deg, #0b1220 0%, #0e1929 100%) !important;
    max-width: 1480px !important;
}}
section[data-testid="stSidebar"] {{
    background: #0b1220 !important;
    border-right: 1px solid #243b53 !important;
}}
section[data-testid="stSidebar"] * {{ color: #9fb3c8 !important; }}
section[data-testid="stSidebar"] [data-testid="stNavLink"] {{
    background: transparent !important;
    color: #9fb3c8 !important;
}}
section[data-testid="stSidebar"] [data-testid="stNavLink"]:hover {{
    background: #16263b !important;
    color: #5eead4 !important;
}}
section[data-testid="stSidebar"] [aria-current="page"] {{
    background: #123b42 !important;
    color: #5eead4 !important;
    box-shadow: inset 3px 0 0 #5eead4;
}}
h1, h2, h3, h4, h5, h6, p, label, [data-testid="stCaptionContainer"] {{
    color: #f4f7fb !important;
}}
.stCaption, [data-testid="stMarkdownContainer"] p {{ color: #9fb3c8 !important; }}
hr {{ border-color: #243b53 !important; opacity: 0.7; }}
[data-testid="stMetric"] {{
    background: #111c2e !important;
    border: 1px solid #243b53 !important;
    border-radius: 16px !important;
    box-shadow: 0 12px 28px rgba(0,0,0,0.18) !important;
}}
[data-testid="stMetricLabel"] {{ color: #9fb3c8 !important; }}
[data-testid="stMetricValue"] {{ color: #f4f7fb !important; }}
[data-testid="stDataFrame"] {{
    background: #111c2e !important;
    border: 1px solid #243b53 !important;
    border-radius: 14px !important;
}}
[data-testid="stDataFrame"] * {{ color: #d9e2ec !important; }}
[data-testid="stExpander"] {{
    background: #111c2e !important;
    border: 1px solid #243b53 !important;
    border-radius: 14px !important;
}}
[data-testid="stExpander"] summary {{ color: #d9e2ec !important; }}
[data-testid="stTabs"] [role="tablist"] {{ border-bottom-color: #243b53 !important; }}
[data-testid="stTabs"] [role="tab"] {{ color: #9fb3c8 !important; }}
[data-testid="stTabs"] [aria-selected="true"] {{ color: #5eead4 !important; }}
[data-testid="stTextInput"] input, [data-testid="stSelectbox"] div, [data-testid="stDateInput"] input {{
    background: #111c2e !important;
    border-color: #243b53 !important;
    color: #f4f7fb !important;
}}
[data-testid="stTextInput"] input::placeholder {{ color: #71869c !important; }}
[data-testid="stButton"] button {{
    background: #16263b !important;
    border: 1px solid #334e68 !important;
    border-radius: 10px !important;
    color: #d9e2ec !important;
}}
[data-testid="stButton"] button:hover {{
    background: #1d3b4d !important;
    border-color: #5eead4 !important;
    color: #5eead4 !important;
}}
[data-testid="stButton"] button[kind="primary"] {{
    background: #0f766e !important;
    border-color: #0f766e !important;
    color: #f0fdfa !important;
}}
[data-testid="stButton"] button[kind="primary"]:hover {{
    background: #14b8a6 !important;
    border-color: #5eead4 !important;
}}
[data-testid="stAlert"] {{ border-radius: 14px !important; }}
.fg-topbar {{
    background: rgba(17,28,46,0.94) !important;
    border: 1px solid #243b53 !important;
    box-shadow: 0 14px 34px rgba(0,0,0,0.22) !important;
}}
.fg-brand, .fg-brand-mark {{ color: #f4f7fb !important; }}
.fg-brand-mark {{ color: #5eead4 !important; }}
.fg-topbar-meta {{ color: #9fb3c8 !important; }}
.fg-stat-card, .fg-panel {{
    background: #111c2e !important;
    border-color: #243b53 !important;
    box-shadow: 0 12px 30px rgba(0,0,0,0.18) !important;
}}
.fg-stat-card.fg-attention {{ background: #2a2415 !important; border-color: #8a651c !important; }}
.fg-stat-card.fg-urgent {{ background: #321b28 !important; border-color: #9f405a !important; }}
.fg-stat-card.fg-healthy {{ background: #102a2e !important; border-color: #1c6b69 !important; }}
.fg-stat-label, .fg-stat-note, .fg-page-subtitle, .fg-subtle, .fg-panel-copy, .fg-queue-meta, .fg-health-label {{
    color: #9fb3c8 !important;
}}
.fg-stat-value, .fg-page-title, .fg-panel-title, .fg-queue-subject, .fg-health-value {{
    color: #f4f7fb !important;
}}
.fg-eyebrow {{ color: #5eead4 !important; }}
.fg-queue-row {{
    background: #111c2e !important;
    border-color: #243b53 !important;
    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
}}
.fg-queue-row:hover {{ background: #16263b !important; border-color: #5eead4 !important; }}
.fg-queue-subject {{ color: #f4f7fb !important; }}
.fg-privacy-banner {{
    background: #102a2e !important;
    border-color: #1c6b69 !important;
    color: #9ff5e8 !important;
}}
.fg-panel-dark {{ background: #081421 !important; border-color: #243b53 !important; }}
.fg-badge-green {{ background: #123b36 !important; color: #6ee7b7 !important; }}
.fg-badge-amber {{ background: #3a2c12 !important; color: #fcd34d !important; }}
.fg-badge-red {{ background: #3b1d2a !important; color: #fda4af !important; }}
.fg-badge-blue {{ background: #123252 !important; color: #7dd3fc !important; }}
.fg-badge-gray {{ background: #1e3045 !important; color: #b8c7d9 !important; }}
.fg-health-row {{ border-color: #243b53 !important; }}
.fg-health-label {{ color: #9fb3c8 !important; }}
.fg-health-value {{ color: #f4f7fb !important; }}
[data-testid="stAlert"] {{ background: #16263b !important; border: 1px solid #334e68 !important; color: #d9e2ec !important; }}
[data-testid="stStatusWidget"] {{ background: #111c2e !important; border-color: #243b53 !important; color: #d9e2ec !important; }}
[data-testid="stStatusWidget"] summary {{ color: #d9e2ec !important; }}
.stToast {{ background: #16263b !important; border: 1px solid #334e68 !important; color: #f4f7fb !important; }}
.stDownloadButton {{ background: #16263b !important; }}
</style>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════════════════

def get_auth_config():
    try:
        config = load_config()
        return config.get("auth", {"enabled": False, "users": []})
    except Exception:
        return {"enabled": False, "users": []}


def _auth_secret() -> str:
    import os
    env_secret = os.getenv("FALLGUARD_AUTH_SECRET")
    if env_secret:
        return env_secret
    try:
        config = load_config()
        return config.get("auth", {}).get("jwt_secret") or config.get("auth", {}).get("secret_key", "fallback-secret-key-change-me")
    except Exception:
        return "fallback-secret-key-change-me"


def _attempt_login(username: str, password: str) -> Optional[dict]:
    auth_config = get_auth_config()
    for user in auth_config.get("users", []):
        if user.get("username") == username and verify_password(password, user.get("password_hash", "")):
            return user
    return None


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        if stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$"):
            import bcrypt
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        salt, h = stored_hash.split("$", 1)
        result = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return result.hex() == h
    except Exception:
        return False


def generate_token(username: str, role: str, secret: str) -> str:
    payload = f"{username}:{role}:{int(time.time())}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def validate_token(token: str, secret: str) -> Optional[dict]:
    try:
        parts = token.rsplit(":", 1)
        if len(parts) != 2:
            return None
        payload, sig = parts
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        username, role, ts = payload.split(":", 2)
        auth_config = get_auth_config()
        expiry_hours = float(auth_config.get("token_expiry_hours", 24) or 24)
        if time.time() - int(ts) > expiry_hours * 3600:
            return None
        for u in auth_config.get("users", []):
            if u.get("username") == username:
                return {
                    "username": username,
                    "role": u.get("role", role),
                    "display_name": u.get("display_name", username),
                    "assigned_subjects": u.get("assigned_subjects", []),
                }
        return {"username": username, "role": role, "display_name": username}
    except Exception:
        return None


def _query_token_enabled() -> bool:
    import os
    return os.getenv("FALLGUARD_ALLOW_QUERY_TOKEN", "false").lower() == "true"


def get_current_user() -> Optional[dict]:
    auth_config = get_auth_config()
    if not auth_config.get("enabled", False):
        import os
        if os.getenv("FALLGUARD_ENV", "development").lower() == "production":
            logger.error("Authentication is disabled in production; refusing guest access")
            return None
        return {"username": "guest", "role": "admin", "display_name": "Guest User"}
    token = st.session_state.get("auth_token")
    if not token and _query_token_enabled():
        token = st.query_params.get("auth_token")
        if isinstance(token, list):
            token = token[0] if token else None
    if not token:
        return None
    user = validate_token(token, _auth_secret())
    if user is None:
        return None
    st.session_state["auth_token"] = token
    st.session_state["auth_user"] = user
    return user


def get_user_permissions(user: dict) -> dict:
    role = user.get("role", "viewer")
    if role == "admin":
        return {"can_acknowledge": True, "can_dismiss": True, "can_escalate": True, "can_export": True, "can_view_all": True, "can_manage_settings": True}
    elif role == "caregiver":
        return {"can_acknowledge": True, "can_dismiss": False, "can_escalate": True, "can_export": True, "can_view_all": False, "can_manage_settings": False}
    elif role == "viewer":
        return {"can_acknowledge": False, "can_dismiss": False, "can_escalate": False, "can_export": False, "can_view_all": False, "can_manage_settings": False}
    return {"can_acknowledge": False, "can_dismiss": False, "can_escalate": False, "can_export": False, "can_view_all": False, "can_manage_settings": False}


def filter_by_role(df: pd.DataFrame, user: dict) -> pd.DataFrame:
    if user.get("role") == "admin" or get_user_permissions(user).get("can_view_all"):
        return df
    if "assigned_subjects" in user:
        allowed = {str(subject) for subject in user.get("assigned_subjects", [])}
    else:
        try:
            config = load_config()
            permissions = config.get("auth", {}).get("role_permissions", {})
            allowed = {
                str(subject)
                for subject in permissions.get(user.get("role", ""), ["S1", "S2", "S3"])
            }
        except Exception:
            allowed = {"S1", "S2", "S3"}
    if "subject_id" not in df.columns:
        return df.iloc[0:0].copy()
    return df[df["subject_id"].astype(str).isin(allowed)]

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG + DATA
# ═══════════════════════════════════════════════════════════════════════════════

def get_dashboard_config() -> dict:
    try:
        config = load_config()
        return config.get("dashboard", {})
    except Exception:
        return {}


def _escalation_config() -> dict:
    """Read the escalation section of config.yaml."""
    try:
        config = load_config()
        return config.get("escalation", {})
    except Exception:
        return {}


def _auto_escalate_stale(alerts_df: pd.DataFrame, max_age_sec: float,
                         notify: bool = False) -> int:
    """Escalate pending alerts older than the threshold; optionally re-email."""
    from alert import AlertManager
    if max_age_sec <= 0 or alerts_df is None or len(alerts_df) == 0:
        return 0
    now = pd.to_datetime(time.time(), unit="s")
    pending = alerts_df[(alerts_df["status"] == "pending") & alerts_df["datetime"].notna()]
    stale_rows = []
    for _, row in pending.iterrows():
        age = (now - row["datetime"]).total_seconds()
        if age > max_age_sec and row.get("id"):
            stale_rows.append(row)
    if not stale_rows:
        return 0
    manager = AlertManager()
    ids = [str(row["id"]) for row in stale_rows]
    updated_ids = manager.bulk_update_alert_ids(ids, "system", "system", "escalated")
    if notify:
        for alert_id in updated_ids:
            record = manager.store.get(alert_id) or {}
            try:
                manager.send_escalation_email(ALERT_LOG, float(record.get("timestamp", 0)))
            except (TypeError, ValueError):
                continue
    return len(updated_ids)


def _escalate_alerts(timestamps: list, user: dict, notify: bool = True,
                     alert_ids: list[str] | None = None) -> int:
    """Set alert(s) to escalated and optionally send follow-up email."""
    from alert import AlertManager
    username = user.get("username", "unknown")
    role = user.get("role", "viewer")
    manager = AlertManager()
    if alert_ids:
        updated_ids = manager.bulk_update_alert_ids(
            alert_ids, username, role, "escalated"
        )
        if not notify:
            return len(updated_ids)
        updated_timestamps: list[float] = []
        for alert_id in updated_ids:
            record = manager.store.get(alert_id) or {}
            try:
                updated_timestamps.append(float(record.get("timestamp", 0)))
            except (TypeError, ValueError):
                continue
    else:
        updated_timestamps = AlertManager.bulk_update_alerts(
            ALERT_LOG, timestamps, username, role, "escalated"
        )
    if notify:
        for timestamp in updated_timestamps:
            manager.send_escalation_email(ALERT_LOG, timestamp)
    return len(updated_timestamps)


def load_alert_history(log_path: Path) -> pd.DataFrame:
    """Load and normalize alert records for display.

    AlertStore supplies stable IDs for legacy records and handles malformed
    lines consistently across dashboard and background workers.
    """
    empty_cols = [
        "id", "datetime", "timestamp", "subject_id", "clip_id", "confidence",
        "tier", "outcome", "response_time", "status", "delivery_status",
        "acknowledged_by", "acknowledged_at", "video_clip_path",
    ]
    records = AlertStore(log_path).read_all()
    if not records:
        return pd.DataFrame(columns=empty_cols)
    df = pd.DataFrame(records)
    rename_map = {
        "fall_event_subject": "subject_id",
        "fall_event_clip": "clip_id",
        "fall_event_confidence": "confidence",
        "fall_event_tier": "tier",
        "grace_period_outcome": "outcome",
        "grace_period_response_time": "response_time",
    }
    df = df.rename(columns=rename_map)
    if "timestamp" in df.columns:
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
    else:
        df["datetime"] = pd.NaT
    defaults = {
        "id": "", "subject_id": "unknown", "clip_id": "N/A", "confidence": 0.0,
        "tier": "low", "outcome": "unknown", "response_time": None,
        "status": "pending", "delivery_status": "unknown", "acknowledged_by": None,
        "acknowledged_at": None, "video_clip_path": None,
    }
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
        if default is not None:
            df[col] = df[col].fillna(default)
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0.0)
    df["acknowledged_at"] = pd.to_numeric(df["acknowledged_at"], errors="coerce")
    df = df.sort_values("datetime", ascending=False, na_position="last").reset_index(drop=True)
    return df


def get_system_status() -> dict:
    """Assemble system health from real sources (config, model file, stream server).

    No hardcoded values: camera/model/uptime come from the actual system.
    """
    try:
        config = load_config()
    except Exception:
        config = {}

    alerts_df = load_alert_history(ALERT_LOG)
    today = pd.Timestamp.now().normalize()
    if "datetime" in alerts_df.columns:
        today_count = int((alerts_df["datetime"] >= today).sum())
    else:
        today_count = 0
    pending = len(alerts_df[alerts_df["status"] == "pending"]) if "status" in alerts_df.columns else 0
    acknowledged = len(alerts_df[alerts_df["status"] == "acknowledged"]) if "status" in alerts_df.columns else 0
    escalated = len(alerts_df[alerts_df["status"] == "escalated"]) if "status" in alerts_df.columns else 0
    cancelled = len(alerts_df[alerts_df["outcome"] == "cancelled"]) if "outcome" in alerts_df.columns else 0

    # ─── Camera / uptime: prefer the live stream server, fall back to config ───
    cam_ok = False
    cam_available = False
    uptime_sec = 0.0
    source_type = "unknown"
    live = {}
    base_url = _stream_base_url(_stream_server_config()) if _is_stream_server_running() else None
    if base_url:
        live = _fetch_stream_metrics(base_url) or {}
        cam_available = bool(live.get("camera_available", False))
        source_type = str(live.get("source_type", "unknown"))
        cam_ok = cam_available
        uptime_sec = float(live.get("uptime_sec", 0) or 0)

    # ─── Model: check that the RF artifact exists and loads ────────────────────
    model_loaded = False
    try:
        model_path = Path(config.get("model", {}).get("rf_path", "models/rf_baseline.joblib"))
        if model_path.exists():
            import joblib
            joblib.load(model_path)
            model_loaded = True
    except Exception:
        model_loaded = False

    # ─── Feature flags: read real config keys (no phantom `enabled` fields) ────
    email_cfg = config.get("email", {})
    email_configured = bool(email_cfg.get("sender") and email_cfg.get("app_password"))
    grace_ok = float(config.get("grace_period", {}).get("timeout_sec", 0) or 0) > 0
    sms_cfg = config.get("sms", {})
    sms_on = bool(sms_cfg.get("enabled", False))

    now = datetime.now()
    return {
        "camera_online": cam_ok,
        "camera_available": cam_available,
        "camera_source_type": source_type,
        "model_loaded": model_loaded,
        "last_check_in": now,
        "uptime_hours": uptime_sec / 3600.0 if uptime_sec > 0 else 0.0,
        "total_alerts_today": today_count,
        "total_pending": pending,
        "total_acknowledged": acknowledged,
        "total_escalated": escalated,
        "cancelled_during_grace": cancelled,
        "grace_period_enabled": grace_ok,
        "email_enabled": email_configured,
        "sms_enabled": sms_on,
    }


def _is_stream_server_running() -> bool:
    """True if the local stream-server thread/HTTP is up."""
    try:
        import stream_server as ss
        server = ss.get_stream_server()
        return server is not None and getattr(server, "_httpd", None) is not None
    except Exception:
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED APP STATE
# ═══════════════════════════════════════════════════════════════════════════════

def _app() -> dict:
    return st.session_state.get("__app", {})


def render_login_page():
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    st.markdown('<div style="height:6rem;"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("\U0001f6e1\ufe0f FallGuard AI")
        st.caption("Privacy-Preserving Elderly Care System")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign in", width="stretch", type="primary")

        if submitted:
            if username and password:
                found = _attempt_login(username, password)
                if found:
                    token = generate_token(found["username"], found.get("role", "viewer"), _auth_secret())
                    st.session_state["auth_token"] = token
                    st.session_state["auth_user"] = {
                        "username": found["username"],
                        "role": found.get("role", "viewer"),
                        "display_name": found.get("display_name", found["username"]),
                        "assigned_subjects": found.get("assigned_subjects", []),
                    }
                    # Query-string tokens are opt-in for development only;
                    # production deployments should use a server-side session.
                    if _query_token_enabled():
                        st.query_params["auth_token"] = token
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.error("Please enter both username and password")
        if __import__("os").environ.get("FALLGUARD_SHOW_DEMO_ACCOUNTS", "false").lower() == "true":
            st.caption("Demo accounts — admin / admin123, caregiver / care123")


def render_sidebar_brand():
    st.markdown(
        """
        <div style="padding:0.35rem 0.2rem 0.8rem 0.2rem;">
          <div style="align-items:center;color:#102a43;display:flex;font-size:1.05rem;font-weight:800;gap:0.55rem;">
            <span class="fg-brand-mark" style="align-items:center;background:#0b1220;border-radius:10px;color:#5eead4;display:inline-flex;height:30px;justify-content:center;width:30px;">✦</span>
            FallGuard
          </div>
          <div style="color:#5eead4;font-size:0.7rem;font-weight:700;letter-spacing:0.12em;margin:0.45rem 0 0 2.45rem;text-transform:uppercase;">Midnight operations</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_user(user: dict):
    display_name = user.get("display_name", user["username"])
    role = user.get("role", "viewer").upper()
    st.divider()
    st.markdown(f"**{display_name}**")
    st.caption(role)
    if st.button("Log out", key="logout_btn", width="stretch"):
        st.session_state.pop("auth_token", None)
        st.session_state.pop("auth_user", None)
        if "auth_token" in st.query_params:
            del st.query_params["auth_token"]
        st.rerun()


def _page_header(icon: str, title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="fg-eyebrow">FALLGUARD / MIDNIGHT OPS</div>
        <div class="fg-page-title">{html.escape(icon)} {html.escape(title)}</div>
        <div class="fg-page-subtitle">{html.escape(subtitle)}</div>
        """,
        unsafe_allow_html=True,
    )


def _status_badge(label: str, tone: str = "gray") -> str:
    return f'<span class="fg-badge fg-badge-{tone}">{html.escape(str(label))}</span>'


def _render_product_topbar(page_title: str, user: dict, status: dict | None = None):
    status = status or {}
    feed_ok = bool(status.get("camera_online"))
    model_ok = bool(status.get("model_loaded"))
    dot_color = "#16a34a" if feed_ok and model_ok else "#d97706"
    feed_label = "Local feed ready" if feed_ok else "Feed needs attention"
    role = html.escape(str(user.get("role", "viewer")).upper())
    st.markdown(
        f"""
        <div class="fg-topbar">
          <div class="fg-brand"><span class="fg-brand-mark">✦</span> FallGuard <span style="color:#9fb3c8;font-weight:600">/ Midnight operations</span></div>
          <div class="fg-topbar-meta"><span class="fg-status-dot" style="background:{dot_color}"></span>{html.escape(feed_label)} · {role} · LOCAL SECURE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_stat_strip(items: list[tuple[str, str, str, str]]):
    cards = []
    for label, value, note, tone in items:
        cards.append(
            f'<div class="fg-stat-card fg-{tone}"><div class="fg-stat-label">{html.escape(label)}</div>'
            f'<div class="fg-stat-value">{html.escape(value)}</div>'
            f'<div class="fg-stat-note">{html.escape(note)}</div></div>'
        )
    st.markdown(f'<div class="fg-status-strip">{"".join(cards)}</div>', unsafe_allow_html=True)


def _render_privacy_banner(text: str = "LOCAL SECURE · Raw frames stay on this device. Notifications contain alert metadata only; recording remains opt-in and local."):
    st.markdown(
        f'<div class="fg-privacy-banner"><span>●</span><span>{html.escape(text)}</span></div>',
        unsafe_allow_html=True,
    )


def _render_health_row(label: str, value: str, tone: str = "gray"):
    badge = _status_badge(value, tone)
    st.markdown(
        f'<div class="fg-health-row"><span class="fg-health-label">{html.escape(label)}</span><span class="fg-health-value">{badge}</span></div>',
        unsafe_allow_html=True,
    )


def show_toast(message: str, icon: str = "\u2705"):
    st.toast(f"{icon} {message}")


def _render_toolbar(current_page_title: str, user: dict):
    _render_product_topbar(current_page_title, user, _app().get("status", {}))
    if current_page_title == "Live Monitor":
        return
    c1, c2 = st.columns([5, 1])
    with c1:
        st.caption("Alerts auto-refresh every 30s · Live Monitor preview updates continuously.")
    with c2:
        if get_user_permissions(user).get("can_export"):
            if st.button("Export CSV", key="export_btn", width="stretch"):
                st.session_state["do_export"] = True


def _maybe_render_export():
    if not st.session_state.get("do_export"):
        return
    alerts_df = _app().get("alerts_df")
    if alerts_df is not None and len(alerts_df) > 0:
        export_df = alerts_df[["id", "datetime", "subject_id", "clip_id", "confidence", "tier", "outcome", "response_time", "status", "delivery_status", "acknowledged_by"]].copy()
        export_df.columns = ["Alert ID", "Time", "Subject ID", "Clip ID", "Confidence", "Tier", "Outcome", "Response Time", "Status", "Delivery", "Acknowledged By"]
        export_df["Time"] = export_df["Time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        csv = export_df.to_csv(index=False)
        st.download_button("\U0001f4e5 Download CSV", csv, "alerts_export.csv", "text/csv")
    st.session_state["do_export"] = False

# ═══════════════════════════════════════════════════════════════════════════════
# ALERT DETAIL (native) — shared by table selection and event inspection
# ═══════════════════════════════════════════════════════════════════════════════

_TIER_COLOR = {"high": "red", "medium": "orange", "low": "green"}
_STATUS_COLOR = {"pending": "orange", "acknowledged": "green", "escalated": "red", "dismissed": "gray", "cancelled": "gray"}


def _cancel_live_alert(alert_id: str | None) -> None:
    """Signal a live grace worker when a dashboard action is taken."""
    if not alert_id:
        return
    try:
        from live_detection import cancel_active_alert
        cancel_active_alert(str(alert_id))
    except Exception as exc:
        logger.debug("No active live grace worker for %s: %s", alert_id, exc)


def _safe_recording_path(value: str | None) -> Path | None:
    if not value:
        return None
    try:
        config = load_config()
        root = resolve_path(
            config.get("recording", {}).get("path", "data/recordings"),
            base=PROJECT_ROOT,
        )
        candidate = Path(value).expanduser()
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        candidate = candidate.resolve()
        if root and root in candidate.parents and candidate.suffix.lower() == ".mp4":
            return candidate
    except (OSError, ValueError):
        pass
    return None


def render_alert_detail(alert_data: dict, user: dict, key_prefix: str = "", expanded: bool = False):
    permissions = get_user_permissions(user)
    conf = float(alert_data.get("confidence", 0) or 0)
    tier = alert_data.get("tier", "low")
    status_val = alert_data.get("status", "pending")
    subject = alert_data.get("subject_id", "")
    clip = alert_data.get("clip_id", "")
    ts = alert_data.get("datetime")
    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if pd.notnull(ts) else "N/A"

    with st.expander(f"{subject} \u00b7 {clip} \u00b7 {int(conf*100)}% \u00b7 {tier} \u00b7 {status_val}", expanded=expanded):
        c1, c2 = st.columns(2)
        c1.markdown("**Time**")
        c1.caption(ts_str)
        c2.markdown("**Response time**")
        c2.caption(str(alert_data.get("response_time", "N/A")))

        st.markdown("**Confidence**")
        st.progress(min(max(conf, 0.0), 1.0))

        b1, b2, b3 = st.columns([1, 1, 4])
        with b1:
            st.badge(tier, color=_TIER_COLOR.get(tier, "gray"))
        with b2:
            st.badge(status_val, color=_STATUS_COLOR.get(status_val, "gray"))
        st.caption(f"Delivery: {alert_data.get('delivery_status', 'unknown')}")
        st.divider()

        video_path = _safe_recording_path(alert_data.get("video_clip_path"))
        if video_path and video_path.exists():
            st.markdown("**Local video clip**")
            st.video(str(video_path))
            with video_path.open("rb") as vf:
                st.download_button(
                    "\U0001f4e5 Download clip", data=vf.read(),
                    file_name=f"{subject}_{clip}.mp4", mime="video/mp4",
                    key=f"dl_clip_{key_prefix}",
                )

        if status_val == "pending":
            ack_by = alert_data.get("acknowledged_by")
            ack_at = alert_data.get("acknowledged_at")
            if ack_by and ack_at and pd.notnull(ack_at):
                ack_at_str = datetime.fromtimestamp(ack_at).strftime("%Y-%m-%d %H:%M:%S") if isinstance(ack_at, (int, float)) else str(ack_at)
                st.caption(f"Acknowledged by {ack_by} at {ack_at_str}")
            cols = st.columns(3)
            with cols[0]:
                if permissions.get("can_acknowledge") and st.button("\u2705 Acknowledge", key=f"ack_{key_prefix}", width="stretch", type="primary"):
                    from alert import AlertManager
                    user_info = st.session_state.get("auth_user", {})
                    AlertManager.acknowledge_alert(
                        ALERT_LOG, alert_data.get("timestamp", 0),
                        user_info.get("username", "unknown"),
                        user_info.get("role", "viewer"), "acknowledged",
                        alert_id=alert_data.get("id"),
                    )
                    _cancel_live_alert(alert_data.get("id"))
                    show_toast(f"Alert for {subject} acknowledged", "\u2705")
                    time.sleep(0.3)
                    st.rerun()
            with cols[1]:
                if permissions.get("can_dismiss") and st.button("\u274c Dismiss", key=f"dismiss_{key_prefix}", width="stretch"):
                    from alert import AlertManager
                    user_info = st.session_state.get("auth_user", {})
                    AlertManager.acknowledge_alert(
                        ALERT_LOG, alert_data.get("timestamp", 0),
                        user_info.get("username", "unknown"),
                        user_info.get("role", "viewer"), "dismissed",
                        alert_id=alert_data.get("id"),
                    )
                    _cancel_live_alert(alert_data.get("id"))
                    show_toast(f"Alert for {subject} dismissed", "\u274c")
                    time.sleep(0.3)
                    st.rerun()
            with cols[2]:
                if permissions.get("can_escalate") and st.button("\U0001f6a8 Escalate", key=f"esc_{key_prefix}", width="stretch"):
                    user_info = st.session_state.get("auth_user", {})
                    _escalate_alerts(
                        [alert_data.get("timestamp", 0)], user_info,
                        notify=_escalation_config().get("notify_on_escalate", True),
                        alert_ids=[str(alert_data.get("id"))] if alert_data.get("id") else None,
                    )
                    _cancel_live_alert(alert_data.get("id"))
                    show_toast(f"Alert for {subject} escalated!", "\U0001f6a8")
                    time.sleep(0.3)
                    st.rerun()
        else:
            st.info(f"This alert has already been {status_val}.")


def _alert_tone(tier: str) -> str:
    return {"high": "red", "medium": "amber", "low": "green"}.get(str(tier).lower(), "gray")


def _status_tone(status: str) -> str:
    return {
        "pending": "amber",
        "acknowledged": "green",
        "escalated": "red",
        "dismissed": "gray",
        "cancelled": "gray",
    }.get(str(status).lower(), "gray")


def _relative_age(timestamp: float) -> str:
    try:
        age = max(0, time.time() - float(timestamp))
    except (TypeError, ValueError):
        return "time unknown"
    if age < 60:
        return f"{int(age)}s ago"
    if age < 3600:
        return f"{int(age // 60)}m ago"
    if age < 86400:
        return f"{int(age // 3600)}h ago"
    return f"{int(age // 86400)}d ago"


def _apply_alert_action(row: dict, action: str, user: dict, key: str):
    """Apply one alert action and keep the live grace worker in sync."""
    from alert import AlertManager

    alert_id = row.get("id")
    timestamp = row.get("timestamp", 0)
    username = user.get("username", "unknown")
    role = user.get("role", "viewer")
    if action in {"acknowledged", "dismissed"}:
        AlertManager.acknowledge_alert(
            ALERT_LOG, timestamp, username, role, action, alert_id=alert_id
        )
        label = "Acknowledged" if action == "acknowledged" else "Dismissed"
        st.toast(f"Alert {label.lower()}", icon="✓" if action == "acknowledged" else "×")
    elif action == "escalated":
        _escalate_alerts(
            [timestamp], user,
            notify=_escalation_config().get("notify_on_escalate", True),
            alert_ids=[str(alert_id)] if alert_id else None,
        )
        st.toast("Alert escalated", icon="🚨")
    _cancel_live_alert(alert_id)


def _render_alert_card(row: dict, user: dict, key: str, show_actions: bool = True):
    subject = str(row.get("subject_id", "unknown"))
    tier = str(row.get("tier", "low"))
    status = str(row.get("status", "pending"))
    confidence = float(row.get("confidence", 0) or 0)
    age = _relative_age(row.get("timestamp", 0))
    with st.container(border=True):
        left, right = st.columns([4, 2])
        with left:
            st.markdown(
                f'<div class="fg-queue-subject">{html.escape(subject)} <span style="color:#9fb3c8;font-weight:500">· {html.escape(str(row.get("clip_id", "N/A")))}</span></div>'
                f'<div class="fg-queue-meta">{html.escape(age)} · {int(confidence * 100)}% confidence · {html.escape(str(row.get("outcome", "pending")))}</div>',
                unsafe_allow_html=True,
            )
        with right:
            st.markdown(
                f'<div style="display:flex;gap:0.4rem;justify-content:flex-end;">{_status_badge(tier, _alert_tone(tier))}{_status_badge(status, _status_tone(status))}</div>',
                unsafe_allow_html=True,
            )
        if show_actions and status == "pending":
            permissions = get_user_permissions(user)
            action_row = st.columns([1, 1, 1, 3])
            if action_row[0].button("Acknowledge", key=f"{key}_ack", width="stretch", type="primary", disabled=not permissions.get("can_acknowledge")):
                _apply_alert_action(row, "acknowledged", user, f"{key}_ack")
                st.rerun()
            if action_row[1].button("Dismiss", key=f"{key}_dismiss", width="stretch", disabled=not permissions.get("can_dismiss")):
                _apply_alert_action(row, "dismissed", user, f"{key}_dismiss")
                st.rerun()
            if action_row[2].button("Escalate", key=f"{key}_escalate", width="stretch", disabled=not permissions.get("can_escalate")):
                _apply_alert_action(row, "escalated", user, f"{key}_escalate")
                st.rerun()
        with st.expander("Event details", expanded=False):
            render_alert_detail(row, user, key_prefix=f"{key}_detail", expanded=False)


def render_overview_page():
    """Caregiver-first command center for monitoring and unresolved work."""
    data = _app()
    alerts = data.get("alerts_df")
    if alerts is None:
        alerts = pd.DataFrame()
    status = data.get("status", {})

    _page_header("⌂", "Overview", "A calm, at-a-glance view of monitoring, alerts, and privacy.")

    pending = alerts[alerts["status"] == "pending"] if len(alerts) else alerts
    source_type = status.get("camera_source_type", "unknown")
    source_label = (
        "Demo preview" if source_type == "synthetic_preview"
        else "Video file" if source_type == "video_file"
        else "RTSP camera" if source_type == "rtsp"
        else "Webcam" if source_type == "real_camera"
        else "Feed offline"
    )
    monitoring_label = "Live" if status.get("camera_online") else "Standby"
    pending_count = int(len(pending))
    attention_tone = "urgent" if pending_count else "healthy"
    attention_note = "Needs caregiver response" if pending_count else "No open actions"
    _render_stat_strip([
        ("Monitoring", monitoring_label, source_label, "healthy" if status.get("camera_online") else "attention"),
        ("Needs attention", str(pending_count), attention_note, attention_tone),
        ("Alerts today", str(status.get("total_alerts_today", 0)), "Recorded events", "healthy" if not status.get("total_alerts_today", 0) else "attention"),
        ("Model state", "Ready" if status.get("model_loaded") else "Unavailable", "Random Forest baseline", "healthy" if status.get("model_loaded") else "urgent"),
    ])

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown('<div class="fg-kicker-row"><div class="fg-panel-title">Needs attention</div><div class="fg-subtle">Priority queue</div></div>', unsafe_allow_html=True)
        if len(pending) == 0:
            st.markdown(
                '<div class="fg-panel" style="background:#f5fffc;border-color:#b7e5dc;"><div class="fg-panel-title" style="color:#087f5b;">All clear</div><div class="fg-panel-copy">No pending caregiver actions. Monitoring can continue in the background.</div></div>',
                unsafe_allow_html=True,
            )
        else:
            for index, (_, row) in enumerate(pending.sort_values("datetime", ascending=True).head(3).iterrows()):
                _render_alert_card(row.to_dict(), data.get("user", {}), f"overview_{index}")
            if len(pending) > 3:
                st.caption(f"+ {len(pending) - 3} more pending alert{'s' if len(pending) - 3 != 1 else ''} in the alert queue.")

    with right:
        st.markdown('<div class="fg-kicker-row"><div class="fg-panel-title">System health</div><div class="fg-subtle">Local runtime</div></div>', unsafe_allow_html=True)
        with st.container(border=True):
            _render_health_row("Camera", source_label, "green" if status.get("camera_online") else "amber")
            _render_health_row("Model", "Ready" if status.get("model_loaded") else "Unavailable", "green" if status.get("model_loaded") else "red")
            _render_health_row("Grace period", "Active" if status.get("grace_period_enabled") else "Disabled", "green" if status.get("grace_period_enabled") else "amber")
            _render_health_row("Notifications", "Configured" if status.get("email_enabled") else "Not configured", "green" if status.get("email_enabled") else "amber")
            _render_health_row("Recording", "Off / local only", "green")
        st.markdown("<div style='height:0.7rem'></div>", unsafe_allow_html=True)
        _render_privacy_banner()

    st.markdown("<div style='height:1.45rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="fg-kicker-row"><div class="fg-panel-title">Recent activity</div><div class="fg-subtle">Latest recorded events</div></div>', unsafe_allow_html=True)
    if len(alerts) == 0:
        st.markdown('<div class="fg-panel"><div class="fg-panel-copy">No alert history yet. Events will appear here as the detector creates them.</div></div>', unsafe_allow_html=True)
    else:
        recent = alerts.sort_values("datetime", ascending=False).head(6)
        for index, (_, row) in enumerate(recent.iterrows()):
            status_value = str(row.get("status", "pending"))
            tier_value = str(row.get("tier", "low"))
            st.markdown(
                f'<div class="fg-queue-row"><div class="fg-queue-main"><div class="fg-queue-subject">{html.escape(str(row.get("subject_id", "unknown")))}</div><div class="fg-queue-meta">{html.escape(str(row.get("datetime", "Unknown time")))} · {int(float(row.get("confidence", 0) or 0) * 100)}% confidence</div></div><div class="fg-queue-right">{_status_badge(tier_value, _alert_tone(tier_value))}{_status_badge(status_value, _status_tone(status_value))}</div></div>',
                unsafe_allow_html=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# ALERTS PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def render_alerts_page():
    data = _app()
    user = data.get("user")

    _page_header("\U0001f514", "Alert Queue", "Review, acknowledge, dismiss, or escalate caregiver events.")

    _render_alerts_body(user)


# Auto-refresh the Alerts data region without re-running the whole app.
# Disabled under automated tests (FG_PAGE) to keep AppTest deterministic.
_ALERTS_AUTOREFRESH = 0 if (__import__("os").environ.get("FG_PAGE")) else 30


@st.fragment(run_every=(_ALERTS_AUTOREFRESH if _ALERTS_AUTOREFRESH else None))
def _render_alerts_body(user: dict):
    alerts_df = filter_by_role(load_alert_history(ALERT_LOG), user)

    if alerts_df is None or len(alerts_df) == 0:
        st.info("No alerts yet. Fall detection events will appear here as they are detected.")
        return

    # ─── Auto-escalate stale pending alerts (Phase 2 - Alert Management) ────────
    esc_cfg = _escalation_config()
    auto_after = float(esc_cfg.get("auto_escalate_after_sec", 0) or 0)
    if auto_after > 0:
        stale_count = _auto_escalate_stale(alerts_df, auto_after,
                                           notify=esc_cfg.get("notify_on_auto_escalate", False))
        if stale_count:
            st.toast(f"{stale_count} stale pending alert{'s' if stale_count != 1 else ''} auto-escalated", icon="\u26a0\ufe0f")
            alerts_df = filter_by_role(load_alert_history(ALERT_LOG), user)

    total = int(len(alerts_df))
    pending = int((alerts_df["status"] == "pending").sum())
    escalated = int((alerts_df["status"] == "escalated").sum())
    high_risk = int((alerts_df["tier"] == "high").sum())

    _render_stat_strip([
        ("All events", str(total), "Current view", "healthy"),
        ("Pending", str(pending), "Needs response", "attention" if pending else "healthy"),
        ("Escalated", str(escalated), "Urgent follow-up", "urgent" if escalated else "healthy"),
        ("High tier", str(high_risk), "Model tier", "attention" if high_risk else "healthy"),
    ])

    # ─── Filters (collapsed by default for a cleaner default view) ────────────
    with st.expander("\U0001f50d Filters", expanded=False):
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        with c1:
            search = st.text_input("\U0001f50d", placeholder="Search subject or clip", key="alert_search", label_visibility="collapsed")
        with c2:
            tier_filter = st.pills("Tier", ["All", "high", "medium", "low"], default="All",
                                   key="alert_tier", label_visibility="collapsed", selection_mode="single")
        with c3:
            status_filter = st.pills("Status", ["All", "pending", "acknowledged", "escalated", "dismissed", "cancelled"],
                                     default="pending", key="alert_status", label_visibility="collapsed", selection_mode="single")
        with c4:
            sort_order = st.selectbox("Sort", ["Newest", "Oldest", "Confidence"], key="alert_sort", label_visibility="collapsed")

        # ─── Date range filter ───────────────────────────────────────────────
        d1, d2 = st.columns(2)
        with d1:
            start_date = st.date_input("From", value=None, key="alert_from")
        with d2:
            end_date = st.date_input("To", value=None, key="alert_to")

    filtered = alerts_df.copy()
    if search:
        s = search.lower()
        mask = (filtered["subject_id"].astype(str).str.lower().str.contains(s, na=False) |
                filtered["clip_id"].astype(str).str.lower().str.contains(s, na=False) |
                filtered["tier"].astype(str).str.lower().str.contains(s, na=False))
        filtered = filtered[mask]
    if tier_filter != "All":
        filtered = filtered[filtered["tier"] == tier_filter]
    if status_filter != "All":
        filtered = filtered[filtered["status"] == status_filter]
    if start_date:
        filtered = filtered[filtered["datetime"].dt.normalize() >= pd.Timestamp(start_date)]
    if end_date:
        # Treat the end date as inclusive for the whole calendar day.
        end_exclusive = pd.Timestamp(end_date) + pd.Timedelta(days=1)
        filtered = filtered[filtered["datetime"] < end_exclusive]

    if len(filtered) == 0:
        st.warning("No alerts match the current filters.")
        return

    if sort_order == "Oldest":
        filtered = filtered.sort_values("datetime", ascending=True)
    elif sort_order == "Confidence":
        filtered = filtered.sort_values("confidence", ascending=False)
    else:
        filtered = filtered.sort_values("datetime", ascending=False)

    st.markdown(
        f'<div class="fg-kicker-row"><div class="fg-panel-title">Alert queue</div><div class="fg-subtle">{len(filtered)} event{"s" if len(filtered) != 1 else ""} in view · actions update the live event state</div></div>',
        unsafe_allow_html=True,
    )
    visible_rows = filtered.head(25)
    if len(visible_rows) == 0:
        st.markdown('<div class="fg-panel"><div class="fg-panel-copy">No alerts match the current filters.</div></div>', unsafe_allow_html=True)
    for index, (_, row) in enumerate(visible_rows.iterrows()):
        _render_alert_card(row.to_dict(), user, f"queue_{index}")
    if len(filtered) > len(visible_rows):
        st.caption(f"Showing the first {len(visible_rows)} events. Refine the filters to narrow the queue.")

    with st.expander("Compact table view", expanded=False):
        display_df = pd.DataFrame({
            "Time": filtered["datetime"].dt.strftime("%m-%d %H:%M"),
            "Subject": filtered["subject_id"].astype(str),
            "Tier": filtered["tier"].astype(str).str.upper(),
            "Confidence": (filtered["confidence"].fillna(0) * 100).astype(int).astype(str) + "%",
            "Status": filtered["status"].astype(str).str.upper(),
            "Delivery": filtered["delivery_status"].astype(str).str.upper(),
        })
        st.dataframe(display_df, hide_index=True, width="stretch")

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE MONITOR PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def _stream_server_config() -> dict:
    try:
        cfg = load_config()
    except Exception:
        cfg = {}
    s = cfg.get("streaming", {})
    r = cfg.get("recording", {})
    cam = cfg.get("camera", {})
    allow_remote = bool(s.get("allow_remote", False))
    if allow_remote:
        logger.warning("streaming.allow_remote is ignored; use an authenticated reverse proxy")
    return {
        "enabled": s.get("enabled", True),
        "host": s.get("host", "127.0.0.1") if not allow_remote else "127.0.0.1",
        "port": int(s.get("port", 8091)),
        "jpeg_quality": int(s.get("jpeg_quality", 80)),
        "max_fps": float(s.get("max_fps", 15)),
        "camera": {
            "source": cam.get("source", cam.get("index", 0)),
            "webcam_source": cam.get("webcam_source", cam.get("index", 0)),
            "demo_source": cam.get("demo_source", "data/demo/demo_fall.mp4"),
            "width": int(cam.get("width", 640)),
            "height": int(cam.get("height", 480)),
            "fps": float(cam.get("fps", 30)),
        },
        "use_synthetic": s.get("use_synthetic", False),
        "recording_enabled": bool(r.get("enabled", False)),
        "allowed_origins": s.get("allowed_origins", [
            "http://localhost:8501", "http://127.0.0.1:8501",
            "http://localhost:3000", "http://127.0.0.1:3000",
        ]),
        "record_path": r.get("path", "data/recordings/"),
        "recording_max_days": int(r.get("max_days", 7)),
        "recording_segment_duration": r.get("segment_duration", 300),
    }


def _start_stream_server() -> Optional[dict]:
    import stream_server as ss
    cfg = _stream_server_config()
    try:
        ss.ensure_stream_server_running(cfg)
    except Exception as e:
        logger.warning(f"Stream server failed to start: {e}")
        return None
    if ss.get_stream_server()._httpd is None:
        return None
    return cfg


def _stream_base_url(cfg: dict = None) -> Optional[str]:
    try:
        import stream_server as ss
        if ss.get_stream_server()._httpd is None:
            return None
        port = int((cfg or {}).get("port", 8091))
        return f"http://127.0.0.1:{port}"
    except Exception:
        return None


def _stream_token() -> str:
    try:
        import stream_server as ss
        return str(ss.get_stream_server().auth_token)
    except Exception:
        return ""


def _fetch_stream_metrics(base_url: str) -> Optional[dict]:
    if not base_url:
        return None
    try:
        request = urllib.request.Request(
            f"{base_url}/metrics",
            headers={"X-FallGuard-Token": _stream_token()},
        )
        with urllib.request.urlopen(request, timeout=3) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _post_stream_action(base_url: str, action: str) -> Optional[dict]:
    if not base_url:
        return None
    try:
        req = urllib.request.Request(
            f"{base_url}/record/{action}",
            method="POST",
            headers={"X-FallGuard-Token": _stream_token()},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.warning(f"Record {action} failed: {e}")
        return None


@st.fragment(run_every=1.0)
def _render_live_metrics(status: dict, alerts_df: pd.DataFrame, base_url: str):
    live = _fetch_stream_metrics(base_url) or {}
    fps = float(live.get("fps", 0.0) or 0.0)
    rec_active = bool(live.get("recording_active", False))
    cam_ok = bool(live.get("camera_available", False))
    source_type = str(live.get("source_type", "unknown"))
    source_label = {
        "synthetic_preview": "Demo preview",
        "video_file": "Video file",
        "rtsp": "RTSP camera",
        "real_camera": "Webcam",
    }.get(source_type, "Offline" if not cam_ok else "Camera")

    now = pd.to_datetime(time.time(), unit="s")
    today = now.normalize()
    if "datetime" in alerts_df.columns and len(alerts_df) > 0:
        last_hour_count = int((alerts_df["datetime"] >= (now - pd.Timedelta(hours=1))).sum())
        today_count = int((alerts_df["datetime"] >= today).sum())
    else:
        last_hour_count = 0
        today_count = 0
    age = live.get("last_frame_age_sec")
    age_str = f"{float(age):.1f}s ago" if age is not None else "Waiting for frame"
    _render_stat_strip([
        ("Live feed", source_label, age_str, "healthy" if cam_ok else "attention"),
        ("Stream rate", f"{fps:.1f} FPS", "Current capture rate", "healthy" if fps > 0 else "attention"),
        ("Alerts / hour", str(last_hour_count), "Rolling one-hour view", "healthy" if not last_hour_count else "attention"),
        ("Alerts today", str(today_count), "Recorded events", "healthy" if not today_count else "attention"),
    ])
    st.caption(f"Recording is {'active and local' if rec_active else 'off'} · remote video access is blocked by the local stream policy.")


def _render_video_panel(base_url: str):
    token = urllib.parse.quote(_stream_token(), safe="")
    frame_url = f"{base_url}/frame?token={token}&t=" if base_url and token else None
    if not frame_url:
        st.markdown(
            '<div class="fg-panel-dark"><div class="fg-panel-title">Live feed unavailable</div><div class="fg-panel-copy" style="color:#b8c7d9;">Start the local stream server or enable streaming in config.yaml to view the camera feed.</div></div>',
            unsafe_allow_html=True,
        )
        return

    iframe_html = f"""
    <div style="position:relative;background:#081421;border:1px solid #243b53;border-radius:18px;overflow:hidden;box-shadow:0 16px 40px rgba(8,20,33,0.22);">
        <img id="fg-live" alt="Live camera feed" style="display:block;width:100%;aspect-ratio:16/9;object-fit:contain;background:#081421;" />
        <div style="position:absolute;top:14px;left:14px;background:rgba(8,20,33,0.84);border:1px solid rgba(94,234,212,0.35);border-radius:999px;color:#5eead4;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;font-weight:800;letter-spacing:0.1em;padding:7px 11px;">
            <span id="fg-dot" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#5eead4;margin-right:7px;"></span>
            <span id="fg-status">CONNECTING</span>
        </div>
        <div style="position:absolute;right:14px;bottom:14px;background:rgba(8,20,33,0.72);border:1px solid rgba(184,199,217,0.2);border-radius:8px;color:#b8c7d9;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;padding:6px 8px;">LOCAL / AUTHENTICATED</div>
    </div>
    <script>
    (function(){{
      var img = document.getElementById('fg-live');
      var status = document.getElementById('fg-status');
      var dot = document.getElementById('fg-dot');
      var base = '{frame_url}';
      var live = false;
      var lastOk = Date.now();
      function tick(){{ img.src = base + Date.now(); }}
      img.onload = function(){{
        if(!live){{ live = true; status.textContent = 'LIVE'; status.style.color = '#5eead4'; dot.style.background = '#5eead4'; }}
        lastOk = Date.now();
        setTimeout(tick, 200);
      }};
      img.onerror = function(){{
        if(live){{ live = false; status.textContent = 'RECONNECTING'; status.style.color = '#fbbf24'; dot.style.background = '#fbbf24'; }}
        setTimeout(tick, 1500);
      }};
      setInterval(function(){{
        if(new Date() - lastOk > 3500 && live){{
          live = false; status.textContent = 'OFFLINE'; status.style.color = '#f87171'; dot.style.background = '#f87171';
        }}
      }}, 1000);
      tick();
    }})();
    </script>
    """
    st.iframe(iframe_html, width="stretch", height=430)


def _parse_segment_start(name: str) -> Optional[float]:
    """Parse segment start time (unix) from `rec_YYYYMMDD_HHMMSS.mp4`."""
    try:
        stem = name.split(".mp4", 1)[0]
        if not stem.startswith("rec_"):
            return None
        return datetime.strptime(stem[4:], "%Y%m%d_%H%M%S").timestamp()
    except Exception:
        return None


def _map_alerts_to_recordings(alerts_df: pd.DataFrame, recordings: list,
                              segment_duration: float = 300.0) -> dict:
    """Map alerts to recording segments by timestamp correlation.

    Returns:
        {segment_name: [{"offset_sec": float, "tier": str, "subject_id": str,
                         "confidence": float, "timestamp": float}, ...]}
    """
    if alerts_df is None or len(alerts_df) == 0 or not recordings:
        return {}
    mapping: dict = {}
    idx_by_name = {}
    for rec in recordings:
        name = rec.get("name", "")
        seg_start = _parse_segment_start(name)
        if seg_start is None:
            continue
        idx_by_name[name] = (seg_start, seg_start + max(float(segment_duration), 1.0))
        mapping.setdefault(name, [])
    if not idx_by_name:
        return mapping
    for _, row in alerts_df.iterrows():
        ts = float(row.get("timestamp") or 0)
        if ts <= 0:
            continue
        for name, (lo, hi) in idx_by_name.items():
            if lo <= ts < hi:
                mapping[name].append({
                    "offset_sec": round(ts - lo, 2),
                    "tier": str(row.get("tier", "low")),
                    "subject_id": str(row.get("subject_id", "unknown")),
                    "confidence": float(row.get("confidence", 0) or 0),
                    "timestamp": ts,
                })
                break
    return {k: v for k, v in mapping.items() if v}


def _fetch_recording_info(base_url: str, name: str) -> Optional[dict]:
    """Fetch metadata for one recording segment via /recordings/<name>/info."""
    if not base_url or not name:
        return None
    try:
        import urllib.parse
        url = f"{base_url}/recordings/{urllib.parse.quote(name)}/info"
        request = urllib.request.Request(
            url, headers={"X-FallGuard-Token": _stream_token()}
        )
        with urllib.request.urlopen(request, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _render_recording_timeline(markers: list, duration_sec: float) -> None:
    """Render a clickable timeline strip with alert markers.

    Each marker is an anchor positioned at `left: (offset/duration*100)%`.
    Clicking sets `?seek=<offset>` which triggers a natural Streamlit rerun.
    """
    if duration_sec <= 0:
        return
    tier_color = {"high": "#fb7185", "medium": "#fbbf24", "low": "#34d399"}
    dots = []
    for mk in sorted(markers, key=lambda m: m["offset_sec"]):
        pct = min(max(mk["offset_sec"] / duration_sec * 100.0, 0.0), 100.0)
        ts = time.strftime(
            "%H:%M:%S", time.localtime(mk.get("timestamp") or 0)
        )
        color = tier_color.get(mk.get("tier", "low"), "#16a34a")
        title = html.escape(
            f"{ts} \u00b7 Tier: {mk.get('tier','low')} \u00b7 "
            f"Conf: {mk.get('confidence',0):.2f} \u00b7 {mk.get('subject_id','')}"
        )
        dots.append(
            f'<a href="?seek={mk["offset_sec"]:.2f}" title="{title}" '
            f'style="position:absolute;top:50%;translate:0 -50%;left:{pct:.2f}%;'
            f'width:14px;height:14px;border-radius:50%;background:{color};'
            f'border:2px solid #fff;box-shadow:0 1px 3px rgba(15,23,42,.5);'
            f'display:inline-block;cursor:pointer;padding:0;text-decoration:none;'
            f'z-index:2;"></a>'
        )
    bar = (
        f'<div style="position:relative;height:24px;border-radius:8px;'
        f'background:linear-gradient(90deg,#243b53,#334e68);overflow:visible;">'
        f"<div style=\"position:absolute;inset:0;margin:auto;height:4px;border-radius:4px;"
        f"background:#334e68;\"></div>{''.join(dots)}</div>"
    )
    st.caption("\u23f3 Timeline \u00b7 click a marker to seek \u00b7 tier colors: high-red, medium-amber, low-green")
    st.html(bar)


def _render_recording_panel(user: dict, base_url: str, cfg: dict = None,
                            alerts_df: pd.DataFrame = None):
    permissions = get_user_permissions(user)
    if not permissions.get("can_manage_settings"):
        return

    rec_path = Path((cfg or {}).get("record_path", "data/recordings"))
    recording_enabled = bool((cfg or {}).get("recording_enabled", False))
    live = _fetch_stream_metrics(base_url) or {}
    rec_active = live.get("recording_active", False)
    supports_recording = live.get("source_type") in {"real_camera", "rtsp"}
    segments = sorted(rec_path.glob("rec_*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
    total_mb = sum(f.stat().st_size for f in segments) / 1024 / 1024

    st.subheader("Recording")
    if not recording_enabled:
        st.info("Recording is disabled by configuration. Existing local segments can still be reviewed below.")
    elif not supports_recording:
        st.info("The active demo/synthetic source does not support recording. Switch to a real camera for opt-in recording.")
    c1, c2 = st.columns([1, 4])
    with c1:
        if rec_active:
            if st.button("\u23f9 Stop", key="rec_stop", width="stretch", disabled=not (recording_enabled and supports_recording)):
                _post_stream_action(base_url, "stop")
                show_toast("Recording stopped", "\u23f9")
                time.sleep(0.3)
                st.rerun()
        else:
            if st.button("\u25cf Record", key="rec_start", width="stretch", type="primary", disabled=not (recording_enabled and supports_recording)):
                _post_stream_action(base_url, "start")
                show_toast("Recording started", "\u25cf")
                time.sleep(0.3)
                st.rerun()
    with c2:
        st.caption(
            f"{'Recording' if rec_active else 'Idle'} \u00b7 "
            f"retention {cfg.get('recording_max_days', 7)} days \u00b7 "
            f"{len(segments)} segments \u00b7 {total_mb:.1f} MB stored"
        )
    st.caption("Privacy first: recording is OFF by default and auto-deletes after the retention window.")

    # ─── Historical playback / timeline scrubbing (Phase 3) ─────────────────
    st.divider()
    st.subheader("Playback")
    if not segments:
        st.caption("No recordings yet. Start recording to generate segments.")
        return

    sel_name = st.selectbox("Recording segment", [f.name for f in segments],
                            key="rec_playback_segment")
    info = _fetch_recording_info(base_url, sel_name) or {}
    duration = float(info.get("duration_sec") or cfg.get("recording_segment_duration", 300) or 300)

    markers = _map_alerts_to_recordings(
        alerts_df, [{"name": sel_name}], segment_duration=duration
    ).get(sel_name, [])
    markers = [m for m in markers if m["offset_sec"] <= duration]
    if markers:
        _render_recording_timeline(markers, duration)
    else:
        st.caption("\u23f3 Timeline \u00b7 no fall alerts in this segment")

    start_time = 0.0
    if "seek" in st.query_params:
        try:
            start_time = min(max(float(st.query_params["seek"]), 0.0), duration)
        except (TypeError, ValueError):
            start_time = 0.0
        try:
            del st.query_params["seek"]
        except Exception:
            pass

    video_path = str(rec_path / sel_name)
    if Path(video_path).exists():
        st.video(video_path, start_time=start_time, format="video/mp4")
    else:
        st.caption("Segment file not found locally.")


def _render_event_inspector(alerts_df: pd.DataFrame, user: dict):
    st.subheader("Fall events")
    if len(alerts_df) == 0:
        st.caption("No fall events yet.")
        return

    recent = alerts_df.sort_values("datetime", ascending=False).head(8).copy()
    options = []
    key_to_pos = {}
    for i, (_, row) in enumerate(recent.iterrows()):
        ts = row["datetime"].strftime("%H:%M:%S") if pd.notnull(row.get("datetime")) else "n/a"
        label = f"{ts} \u00b7 {row.get('subject_id','')} \u00b7 {int((row.get('confidence',0) or 0)*100)}% \u00b7 {row.get('tier','low')}"
        options.append(label)
        key_to_pos[label] = i

    selected = st.selectbox("Inspect event", options, key="live_event_select")
    if selected and selected in key_to_pos:
        row = recent.iloc[key_to_pos[selected]]
        alert_data = row.to_dict()
        alert_data["datetime"] = row.get("datetime")
        render_alert_detail(alert_data, user, key_prefix=f"live_{key_to_pos[selected]}", expanded=True)


def _current_stream_source() -> Optional[object]:
    """Return the active stream-server camera source value or None."""
    try:
        import stream_server as ss
        server = ss.get_stream_server()
        if server is None:
            return None
        cam_cfg = server.config.get("camera", {})
        return cam_cfg.get("source", None)
    except Exception:
        return None


def _render_source_toggle():
    """Live Monitor input-source toggle: Live webcam <-> Preloaded video.

    Each switch re-opens the camera on the new source and starts a fresh
    fall-detection session, which runs a full grace period and then sends one
    alert (email + alert-log entry) for the newly active source.
    """
    cfg = _stream_server_config()
    cam = cfg.get("camera", {})
    webcam_src = cam.get("webcam_source", 0)
    demo_src = cam.get("demo_source", "data/demo/demo_fall.mp4")

    current = _current_stream_source()
    if current is None:
        current = webcam_src

    def _is_index(v):
        return isinstance(v, int) or (isinstance(v, str) and v.isdigit())

    label = "Live webcam" if (
        _is_index(current) and str(current) == str(webcam_src)
    ) else "Preloaded video"
    default_idx = 0 if label == "Live webcam" else 1

    st.markdown(
        '<div class="fg-kicker-row"><div class="fg-panel-title">Input source</div><div class="fg-subtle">Switching starts a fresh detection session</div></div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([3, 1])
    with c1:
        choice = st.radio(
            "Input source",
            ["Live webcam", "Preloaded video"],
            index=default_idx,
            horizontal=True,
            key="live_source_toggle",
        )
    with c2:
        st.caption("Switch starts a new fall-detection session on the selected source.")

    want = webcam_src if choice == "Live webcam" else demo_src

    if "live_source_applied" not in st.session_state:
        st.session_state["live_source_applied"] = str(current)

    if str(want) != st.session_state["live_source_applied"]:
        st.session_state["live_source_applied"] = str(want)
        import stream_server as ss
        try:
            server = ss.get_stream_server()
            if server is not None:
                server.switch_source(want)
            from live_detection import get_live_detector
            detector = get_live_detector()
            detector.run_session(want)
            show_toast(f"Detection session started on {choice}", "\U0001f4f9")
        except Exception as e:
            st.warning(f"Failed to switch source: {e}")
        time.sleep(0.3)
        st.rerun()

    # Status line for the active session
    try:
        from live_detection import get_live_detector
        detector = get_live_detector()
        status = detector.status()
        parts = [f"Active source: **{choice}**"]
        if status.get("active"):
            parts.append(f"Detection session **running** (grace \u2248 {status.get('grace_timeout_sec', 20)}s)")
        else:
            parts.append("Detection session **idle**")
        if status.get("last_alert_at"):
            parts.append("last alert " + time.strftime(
                "%H:%M:%S", time.localtime(status["last_alert_at"])
            ))
        st.caption(" \u00b7 ".join(parts))
    except Exception:
        pass


def render_live_monitor():
    data = _app()
    base_url = data.get("base_url")
    alerts_df = data.get("alerts_df")
    if alerts_df is None:
        alerts_df = pd.DataFrame()

    _page_header("\U0001f4f9", "Live Monitor", "Real-time fall detection preview.")

    # ─── Input source toggle (live webcam <-> preloaded video) ─────────────
    _render_source_toggle()

    _render_video_panel(base_url)

    try:
        _render_live_metrics(data.get("status", {}), alerts_df, base_url)
    except Exception as e:
        st.warning(f"Live metrics unavailable: {e}")

    with st.expander("\u23fa\ufe0f Recording & Playback", expanded=False):
        _render_recording_panel(data.get("user"), base_url, _stream_server_config(), alerts_df)
    _render_event_inspector(alerts_df, data.get("user"))

# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def render_analytics():
    data = _app()
    alerts_df = data.get("alerts_df")

    _page_header("\U0001f4ca", "Analytics", "Detection performance and trends.")

    if alerts_df is None or len(alerts_df) == 0:
        st.info("Analytics will appear once alerts are generated by the detection system.")
        return

    # ─── Global date filter (consistent with Alerts page) ────────────────────
    d1, d2 = st.columns(2)
    with d1:
        start_date = st.date_input("From", value=None, key="analytics_from")
    with d2:
        end_date = st.date_input("To", value=None, key="analytics_to")
    if start_date or end_date:
        alerts_df = alerts_df[alerts_df["datetime"].notna()].copy()
        if start_date:
            alerts_df = alerts_df[alerts_df["datetime"].dt.normalize() >= pd.Timestamp(start_date)]
        if end_date:
            alerts_df = alerts_df[alerts_df["datetime"].dt.normalize() <= pd.Timestamp(end_date)]
        if len(alerts_df) == 0:
            st.warning("No alerts match the current date range.")
            return

    def _cnt(col, val):
        return int((alerts_df[col] == val).sum()) if col in alerts_df.columns else 0

    total = int(len(alerts_df))
    avg_conf = float(alerts_df["confidence"].fillna(0).mean())
    high_risk = _cnt("tier", "high")
    pending = _cnt("status", "pending")
    escalated = _cnt("status", "escalated")

    m = st.columns(5)
    m[0].metric("Total alerts", total)
    m[1].metric("Avg confidence", f"{avg_conf*100:.0f}%")
    m[2].metric("High tier", high_risk)
    m[3].metric("Pending", pending)
    m[4].metric("Escalated", escalated)

    # ─── Response-time metrics (alerts that were actioned) ──────────────────
    actioned = alerts_df[alerts_df["acknowledged_at"].notna()].copy()
    if len(actioned) > 0:
        actioned["response_sec"] = actioned["acknowledged_at"] - actioned["timestamp"]
        actioned = actioned[actioned["response_sec"] >= 0]
    n_actioned = len(actioned)
    mean_tt = float(actioned["response_sec"].mean()) / 60 if n_actioned else None
    median_tt = float(actioned["response_sec"].median()) / 60 if n_actioned else None
    p95_tt = float(actioned["response_sec"].quantile(0.95)) / 60 if n_actioned else None

    m2 = st.columns(4)
    m2[0].metric("Avg response", f"{mean_tt:.1f} min" if mean_tt is not None else "\u2014")
    m2[1].metric("Median response", f"{median_tt:.1f} min" if median_tt is not None else "\u2014")
    m2[2].metric("P95 response", f"{p95_tt:.1f} min" if p95_tt is not None else "\u2014")
    m2[3].metric("Actioned alerts", int(n_actioned))

    # ─── CSV export (respects role-filtered alert history) ──────────────────
    export_cols = ["id", "datetime", "timestamp", "subject_id", "clip_id", "confidence",
                   "tier", "status", "delivery_status", "acknowledged_by", "acknowledged_at",
                   "outcome", "response_time"]
    export_df = alerts_df[[c for c in export_cols if c in alerts_df.columns]].copy()
    if "datetime" in export_df.columns:
        export_df["datetime"] = export_df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    if "acknowledged_at" in export_df.columns:
        export_df["acknowledged_at"] = pd.to_datetime(
            export_df["acknowledged_at"], unit="s", errors="coerce"
        ).dt.strftime("%Y-%m-%d %H:%M:%S")
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "\u2b07\ufe0f Export CSV",
        csv_bytes,
        file_name=f"fall_alerts_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        width="stretch",
    )
    st.caption("Exports all alerts visible in this view as CSV.")
    st.divider()

    tab_trend, tab_breakdown, tab_conf, tab_subjects, tab_response = st.tabs([
        "Trend", "Breakdown", "Confidence", "Subjects", "Response",
    ])

    with tab_trend:
        valid = alerts_df[alerts_df["datetime"].notna()].copy()
        if len(valid) > 0:
            # ─── Week-over-week delta ─────────────────────────────────────────────
            now = pd.to_datetime(time.time(), unit="s").normalize()
            week_ago = now - pd.Timedelta(days=7)
            this_week = valid[valid["datetime"] >= week_ago]
            last_week = valid[(valid["datetime"] >= (now - pd.Timedelta(days=14))) & (valid["datetime"] < week_ago)]
            this_n, last_n = len(this_week), len(last_week)
            delta = this_n - last_n
            pct = delta / max(last_n, 1) * 100

            m_wow = st.columns(4)
            m_wow[0].metric("This week", this_n)
            m_wow[1].metric("Last week", last_n)
            m_wow[2].metric("\u0394 vs last week", f"{delta:+d} ({pct:+.0f}%)")
            m_wow[3].metric("Daily avg", f"{this_n / 7:.1f}")

            valid["date"] = valid["datetime"].dt.normalize()
            counts = valid.groupby("date").size()
            idx = pd.date_range(end=pd.to_datetime(time.time(), unit="s").normalize(), periods=14, freq="D")
            cnt = counts.reindex(idx).fillna(0).astype(int)
            trend_df = pd.DataFrame({"Date": idx.strftime("%m-%d"), "Alerts": cnt.values})
            st.line_chart(trend_df, x="Date", y="Alerts", color=_PRIMARY)
            st.caption("Alerts per day, trailing 14 days.")

            # ─── Hour × weekday heatmap (zero-dep CSS grid) ───────────────────────
            st.markdown("**Alert patterns by hour & weekday**")
            vh = valid.copy()
            vh["hour"] = vh["datetime"].dt.hour
            vh["weekday"] = vh["datetime"].dt.weekday  # 0=Mon
            grid = vh.groupby(["weekday", "hour"]).size().unstack(fill_value=0)
            grid = grid.reindex(index=range(7), columns=range(24), fill_value=0).astype(int)
            max_val = int(grid.values.max()) if grid.size else 1

            html = ['<div style="display:grid;grid-template-columns:48px repeat(24,1fr);gap:3px;font-size:11px;">']
            html.append('<div></div>' + "".join(
                f'<div style="text-align:center;color:#9fb3c8;">{h:02d}</div>' for h in range(24)))
            wd_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for wd in range(7):
                html.append(f'<div style="text-align:right;padding-right:6px;color:#9fb3c8;">{wd_labels[wd]}</div>')
                for h in range(24):
                    v = int(grid.iloc[wd, h])
                    intensity = min(v / max_val, 1.0) if max_val else 0.0
                    r = int(15 + 20 * intensity)
                    g = int(35 + 120 * intensity)
                    b = int(55 + 100 * intensity)
                    cell_info = f"Alerts: {v}" if v else "No alerts"
                    label = str(v) if v else "\u00b7"
                    color = "#d9e2ec"
                    html.append(
                        f'<div style="background:rgb({r},{g},{b});border-radius:3px;height:22px;'
                        f'display:flex;align-items:center;justify-content:center;color:{color};'
                        f'title="{cell_info}">{label}</div>')
            html.append('</div>')
            st.html("".join(html))
            st.caption("Alert frequency by hour & weekday (darker = more alerts).")
        else:
            st.caption("No dated alerts available.")

    with tab_breakdown:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("By tier")
            tc = alerts_df["tier"].value_counts().to_dict()
            st.bar_chart(pd.DataFrame(tc.items(), columns=["Tier", "Count"]), x="Tier", y="Count", color=_AMBER)
        with c2:
            st.subheader("By status")
            sc = alerts_df["status"].value_counts().to_dict()
            st.bar_chart(pd.DataFrame(sc.items(), columns=["Status", "Count"]), x="Status", y="Count", color=_PRIMARY)

        # ─── Escalation funnel (horizontal bars) ─────────────────────────────────
        st.subheader("Escalation funnel")
        stages = [
            ("Pending", int((alerts_df["status"] == "pending").sum())),
            ("Acknowledged", int((alerts_df["status"] == "acknowledged").sum())),
            ("Escalated", int((alerts_df["status"] == "escalated").sum())),
            ("Dismissed", int((alerts_df["status"] == "dismissed").sum())),
        ]
        total = sum(v for _, v in stages)
        funnel_df = pd.DataFrame(stages, columns=["Stage", "Count"]).set_index("Stage")
        st.bar_chart(funnel_df["Count"], horizontal=True, color=_PRIMARY)
        if total > 0:
            pending_n = stages[0][1]
            acked_n = stages[1][1]
            esc_n = stages[2][1]
            st.caption(
                f"Total alerts in view: {total} | Acknowledged {acked_n}/{pending_n} "
                f"({acked_n / max(pending_n, 1) * 100:.0f}%) | Escalated {esc_n}/{pending_n} "
                f"({esc_n / max(pending_n, 1) * 100:.0f}%)"
            )
        else:
            st.caption("Total alerts in view: 0")

    with tab_conf:
        conf_data = alerts_df["confidence"].dropna()
        if len(conf_data) > 0:
            bins = np.arange(0, 1.05, 0.05).tolist()
            hist, edges = np.histogram(conf_data, bins=bins)
            conf_df = pd.DataFrame({
                "Range": [f"{int(edges[i]*100)}-{int(edges[i+1]*100)}%" for i in range(len(hist))],
                "Count": hist,
            })
            st.bar_chart(conf_df, x="Range", y="Count", color=_GREEN)
        else:
            st.caption("No confidence values recorded.")

    with tab_subjects:
        subjects = alerts_df["subject_id"].dropna().unique()
        if len(subjects) == 0:
            st.caption("No subjects recorded.")
        else:
            for sid in subjects:
                sub_df = alerts_df[alerts_df["subject_id"] == sid]

                acked_sub = sub_df[sub_df["acknowledged_at"].notna()].copy()
                if len(acked_sub) > 0:
                    acked_sub["response_sec"] = acked_sub["acknowledged_at"] - acked_sub["timestamp"]
                    acked_sub = acked_sub[acked_sub["response_sec"] >= 0]
                avg_resp = float(acked_sub["response_sec"].mean()) / 60 if len(acked_sub) > 0 else None

                esc_rate = (sub_df["status"] == "escalated").mean() * 100 if len(sub_df) else 0.0
                high_risk_n = int((sub_df["tier"] == "high").sum())
                avg_conf = float(sub_df["confidence"].fillna(0).mean())

                with st.container(border=True):
                    sub_h, sub_c = st.columns([1, 3])
                    with sub_h:
                        st.subheader(f"Subject {sid}")
                        st.caption(f"{avg_conf*100:.0f}% avg conf \u00b7 {esc_rate:.0f}% escalated")
                    with sub_c:
                        valid = sub_df[sub_df["datetime"].notna()].copy()
                        if len(valid) > 0:
                            valid["date"] = valid["datetime"].dt.normalize()
                            counts = valid.groupby("date").size()
                            idx = pd.date_range(end=pd.to_datetime(time.time(), unit="s").normalize(), periods=14, freq="D")
                            cnt = counts.reindex(idx).fillna(0).astype(int)
                            trend_series = pd.DataFrame({
                                "Day": idx.strftime("%m-%d"),
                                "Alerts": cnt.values,
                            })
                            st.line_chart(trend_series, x="Day", y="Alerts", color=_PRIMARY, height=90)
                        else:
                            st.caption("No dated alerts for this subject.")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Alerts", len(sub_df))
                    c2.metric("High tier", high_risk_n)
                    c3.metric("Avg response", f"{avg_resp:.1f} min" if avg_resp is not None else "\u2014")
                    c4.metric("Escalation", f"{esc_rate:.0f}%")

    with tab_response:
        if len(actioned) > 0:
            hist, edges = np.histogram(actioned["response_sec"] / 60, bins=20)
            resp_df = pd.DataFrame({
                "Minutes": [f"{int(edges[i])}-{int(edges[i+1])}" for i in range(len(hist))],
                "Count": hist,
            })
            st.bar_chart(resp_df, x="Minutes", y="Count", color=_PRIMARY)
            st.caption("Time from alert to acknowledgment (minutes) for actioned alerts.")
        else:
            st.caption("No actioned alerts yet.")

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def render_settings_page():
    data = _app()
    status = data.get("status", {})

    _page_header("\u2699\ufe0f", "Settings", "System health, service status, and privacy.")

    tab_health, tab_privacy = st.tabs(["Health", "Privacy & Compliance"])

    with tab_health:
        # ─── Health KPIs ────────────────────────────────────────────────────
        uptime_h = status.get("uptime_hours", 0.0)
        uptime_str = f"{uptime_h:.1f} h" if uptime_h > 0 else "n/a"
        _render_stat_strip([
            ("Uptime", uptime_str, "Current process", "healthy" if uptime_h > 0 else "attention"),
            ("Alerts today", str(status.get("total_alerts_today", 0)), "Recorded events", "healthy" if not status.get("total_alerts_today", 0) else "attention"),
            ("Pending", str(status.get("total_pending", 0)), "Needs response", "attention" if status.get("total_pending", 0) else "healthy"),
            ("Escalated", str(status.get("total_escalated", 0)), "Urgent follow-up", "urgent" if status.get("total_escalated", 0) else "healthy"),
        ])

        cam_ok = status.get("camera_online", False)
        cam_available = status.get("camera_available", False)
        model_ok = status.get("model_loaded", False)
        grace = status.get("grace_period_enabled", False)
        email_ok = status.get("email_enabled", False)
        sms_ok = status.get("sms_enabled", False)

        c1, c2 = st.columns(2)
        with c1:
            cam_label = "Camera \u2014 Online" if cam_ok else ("Camera \u2014 No feed" if cam_available else "Camera \u2014 Offline")
            with st.status(f"Camera \u2014 {'Online' if cam_ok else 'Offline'}", expanded=False) as s:
                if cam_ok:
                    st.write(f"Live feed available ({cam_available}).")
                else:
                    st.write("No local camera feed detected. The stream server may be offline or using a video source.")
                s.update(label=cam_label, state="complete" if cam_ok else ("running" if cam_available else "error"))
            with st.status("Grace period", expanded=False) as s:
                st.write("Configurable delay before an alert is considered final.")
                s.update(label=f"Grace period \u2014 {'Active' if grace else 'Disabled'}", state="complete" if grace else "running")
            with st.status("Email alerts", expanded=False) as s:
                st.write("Notification channel for fall alerts.")
                s.update(label=f"Email \u2014 {'Configured' if email_ok else 'Not configured'}",
                         state="complete" if email_ok else "running")
            with st.status("SMS alerts", expanded=False) as s:
                st.write("Optional SMS notification channel.")
                s.update(label=f"SMS \u2014 {'Active' if sms_ok else 'Disabled'}",
                         state="complete" if sms_ok else "running")
        with c2:
            with st.status("ML model", expanded=False) as s:
                st.write("Pose-estimation model used for fall detection.")
                s.update(label=f"ML model \u2014 {'Loaded' if model_ok else 'Not loaded'}",
                         state="complete" if model_ok else "error")
            with st.status("Alerts cancelled during grace period", expanded=False) as s:
                st.write(f"{status.get('cancelled_during_grace', 0)} events were cancelled before escalation.")
                s.update(label=f"{status.get('cancelled_during_grace', 0)} cancelled", state="complete")
            st.metric("Alerts acknowledged", status.get("total_acknowledged", 0))
            st.metric("Alerts pending", status.get("total_pending", 0))

    with tab_privacy:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.subheader("Privacy-first design")
            st.markdown(
                "- **Raw-frame storage** — disabled by default; opt-in recordings remain local.\n"
                "- **Remote video transmission** — disabled for the local stream server.\n"
                "- **Pose-only processing** — numeric keypoints are analyzed in memory.\n"
                "- **Alert-only output** — notification payloads contain alert metadata, not video.\n"
                "- **Local processing** — inference runs on the device.\n"
                "- **Retention controls** — recording and alert retention are configurable."
            )
            st.divider()
            st.info("Recording is opt-in, admin-only, and auto-deletes after the retention window.")

        with c2:
            st.subheader("Deployment readiness")
            with st.status("Local processing", expanded=False) as s:
                st.write("Camera frames are processed on this device.")
                s.update(state="complete")
            with st.status("Remote video access", expanded=False) as s:
                st.write("Direct remote streaming is disabled; use a secured proxy for remote access.")
                s.update(state="complete")
            with st.status("Compliance review", expanded=False) as s:
                st.write("Compliance status requires an organization-specific legal and security review.")
                s.update(label="Review required", state="running")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — native navigation router (+ test override via FG_PAGE env)
# ═══════════════════════════════════════════════════════════════════════════════

_PAGE_RUNNERS = {
    "overview": render_overview_page,
    "alerts": render_alerts_page,
    "live": render_live_monitor,
    "analytics": render_analytics,
    "settings": render_settings_page,
}


def main():
    st.set_page_config(
        page_title="FallGuard AI \u2014 Elderly Care System",
        page_icon="\U0001f6e1\ufe0f",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(THEME_CSS, unsafe_allow_html=True)

    try:
        runtime_config = load_config()
        config_errors = validate_config(runtime_config)
    except Exception as exc:
        config_errors = [str(exc)]
    if config_errors:
        st.error("Configuration must be fixed before the dashboard can start:")
        for error in config_errors:
            st.caption(f"• {error}")
        st.stop()

    user = get_current_user()
    if not user:
        render_login_page()
        return

    alerts_df = filter_by_role(load_alert_history(ALERT_LOG), user)
    status = get_system_status()

    stream_cfg = _stream_server_config()
    if stream_cfg.get("enabled", True):
        _start_stream_server()
    base_url = _stream_base_url(stream_cfg)

    st.session_state["__app"] = {
        "user": user,
        "alerts_df": alerts_df,
        "status": status,
        "base_url": base_url,
    }

    # Automated-test override: render one page directly, bypassing navigation.
    force = __import__("os").environ.get("FG_PAGE")
    if force in _PAGE_RUNNERS:
        _PAGE_RUNNERS[force]()
        return

    with st.sidebar:
        render_sidebar_brand()
        nav = st.navigation({
            "Operations": [
                st.Page(render_overview_page, title="Overview", icon="🏠", url_path="overview", default=True),
                st.Page(render_alerts_page, title="Alerts", icon="\U0001f514", url_path="alerts"),
                st.Page(render_live_monitor, title="Live Monitor", icon="\U0001f4f9", url_path="live"),
            ],
            "Insights": [
                st.Page(render_analytics, title="Analytics", icon="\U0001f4ca", url_path="analytics"),
            ],
            "System": [
                st.Page(render_settings_page, title="Settings", icon="\u2699\ufe0f", url_path="settings"),
            ],
        }, position="sidebar")
        render_sidebar_user(user)

    current_page_title = nav.title
    _render_toolbar(current_page_title, user)
    _maybe_render_export()
    nav.run()


if __name__ == "__main__":
    main()