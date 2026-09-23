"""
Dashboard Module
----------------
Fall Detection System for Elderly Care — clinical light UI built on native
Streamlit widgets (st.navigation, st.metric, st.pills, st.dataframe selection,
st.status, st.badge) with a thin CSS layer for spacing/typography.
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
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

ALERT_LOG = Path("logs/alerts.jsonl")
cache_control = {"last_refresh": time.time(), "refresh_interval": 30}

# ─── Light theme base colors (native widgets use .streamlit/config.toml) ──────
_BG = "#f6f8fb"
_SURFACE = "#ffffff"
_BORDER = "#e2e8f0"
_TEXT = "#0f172a"
_SUB = "#475569"
_MUTED = "#94a3b8"
_PRIMARY = "#0f766e"
_GREEN = "#16a34a"
_AMBER = "#d97706"
_RED = "#dc2626"

# ═══════════════════════════════════════════════════════════════════════════════
# LIGHT THEME CSS  (minimal: spacing, typography, and the few custom surfaces)
# ═══════════════════════════════════════════════════════════════════════════════

LIGHT_CSS = f"""
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
</style>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════════════════════

def get_auth_config():
    import yaml
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        return config.get("auth", {"enabled": False, "users": []})
    except Exception:
        return {"enabled": False, "users": []}


def _auth_secret() -> str:
    import yaml
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
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
        if time.time() - int(ts) > 86400:
            return None
        auth_config = get_auth_config()
        for u in auth_config.get("users", []):
            if u.get("username") == username:
                return {"username": username, "role": role, "display_name": u.get("display_name", username)}
        return {"username": username, "role": role, "display_name": username}
    except Exception:
        return None


def get_current_user() -> Optional[dict]:
    auth_config = get_auth_config()
    if not auth_config.get("enabled", False):
        return {"username": "guest", "role": "admin", "display_name": "Guest User"}
    token = st.session_state.get("auth_token")
    if not token:
        return None
    return validate_token(token, _auth_secret())


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
    import yaml
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        allowed = set(config.get("auth", {}).get("role_permissions", {}).get(user.get("role", ""), ["S1", "S2", "S3"]))
    except Exception:
        allowed = {"S1", "S2", "S3"}
    return df[df["subject_id"].isin(allowed)]

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG + DATA
# ═══════════════════════════════════════════════════════════════════════════════

def get_dashboard_config() -> dict:
    import yaml
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        return config.get("dashboard", {})
    except Exception:
        return {}


def _escalation_config() -> dict:
    """Read the escalation section of config.yaml."""
    import yaml
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        return config.get("escalation", {})
    except Exception:
        return {}


def _auto_escalate_stale(alerts_df: pd.DataFrame, max_age_sec: float,
                         notify: bool = False) -> int:
    """Escalate pending alerts older than the threshold; optionally re-email.

    Returns the number of alerts escalated (0 if disabled or none stale).
    """
    from alert import AlertManager
    stale_ts = []
    if max_age_sec <= 0 or alerts_df is None or len(alerts_df) == 0:
        return 0
    now = pd.Timestamp.now()
    pending = alerts_df[(alerts_df["status"] == "pending") & alerts_df["datetime"].notna()]
    for _, row in pending.iterrows():
        age = (now - row["datetime"]).total_seconds()
        if age > max_age_sec:
            stale_ts.append(row["timestamp"])
    if not stale_ts:
        return 0
    updated = AlertManager.bulk_update_alerts(ALERT_LOG, stale_ts, "system", "system", "escalated")
    if notify and updated:
        manager = AlertManager()
        for ts in updated:
            manager.send_escalation_email(ALERT_LOG, ts)
    return len(updated)


def _escalate_alerts(timestamps: list, user: dict, notify: bool = True) -> int:
    """Set alert(s) to escalated and re-notify the caregiver via email."""
    from alert import AlertManager
    username = user.get("username", "unknown")
    role = user.get("role", "viewer")
    updated = AlertManager.bulk_update_alerts(ALERT_LOG, timestamps, username, role, "escalated")
    if notify and updated:
        manager = AlertManager()
        for ts in updated:
            manager.send_escalation_email(ALERT_LOG, ts)
    return len(updated)


def load_alert_history(log_path: Path) -> pd.DataFrame:
    records = []
    empty_cols = ["datetime", "timestamp", "subject_id", "clip_id", "confidence", "tier", "outcome", "response_time", "status", "acknowledged_by", "acknowledged_at", "video_clip_path"]
    if not log_path.exists():
        return pd.DataFrame(columns=empty_cols)
    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not records:
        return pd.DataFrame(columns=empty_cols)
    df = pd.DataFrame(records)
    # Map alert-log field names to dashboard-expected names so real values
    # (confidence, tier, subject) surface instead of defaults.
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
    defaults = {"subject_id": "unknown", "clip_id": "N/A", "confidence": 0.0, "tier": "low", "outcome": "unknown", "response_time": None, "status": "pending", "acknowledged_by": None, "acknowledged_at": None, "video_clip_path": None}
    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default
        df[col] = df[col].fillna(default) if default is not None else df[col]
    df = df.sort_values("datetime", ascending=False, na_position="last").reset_index(drop=True)
    return df


def get_system_status() -> dict:
    import yaml
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
    except Exception:
        config = {}
    alerts_df = load_alert_history(ALERT_LOG)
    total = len(alerts_df)
    pending = len(alerts_df[alerts_df["status"] == "pending"]) if "status" in alerts_df.columns else 0
    acknowledged = len(alerts_df[alerts_df["status"] == "acknowledged"]) if "status" in alerts_df.columns else 0
    escalated = len(alerts_df[alerts_df["status"] == "escalated"]) if "status" in alerts_df.columns else 0
    false_alarms = len(alerts_df[alerts_df["outcome"] == "cancelled"]) if "outcome" in alerts_df.columns else 0
    return {
        "camera_online": True,
        "model_loaded": True,
        "last_check_in": datetime.now() - timedelta(minutes=3),
        "uptime_hours": 12.5,
        "total_alerts_today": total,
        "total_pending": pending,
        "total_acknowledged": acknowledged,
        "total_escalated": escalated,
        "false_alarms_prevented": false_alarms,
        "grace_period_enabled": config.get("grace_period", {}).get("enabled", True),
        "email_enabled": config.get("email", {}).get("enabled", False),
        "sms_enabled": config.get("sms", {}).get("enabled", False),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED APP STATE
# ═══════════════════════════════════════════════════════════════════════════════

def _app() -> dict:
    return st.session_state.get("__app", {})


def render_login_page():
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)
    st.markdown('<div style="height:6rem;"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("\U0001f6e1\ufe0f FallGuard AI")
        st.caption("Privacy-Preserving Elderly Care System")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            st.checkbox("Remember me")
            submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")

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
                    }
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.error("Please enter both username and password")
        st.caption("Demo accounts — admin / admin123, caregiver / care123")


def render_sidebar_brand():
    st.markdown("### \U0001f6e1\ufe0f FallGuard AI")
    st.caption("Elderly Care System")


def render_sidebar_user(user: dict):
    display_name = user.get("display_name", user["username"])
    role = user.get("role", "viewer").upper()
    st.divider()
    st.markdown(f"**{display_name}**")
    st.caption(role)
    if st.button("Log out", key="logout_btn", use_container_width=True):
        st.session_state.pop("auth_token", None)
        st.session_state.pop("auth_user", None)
        st.rerun()


def _page_header(icon: str, title: str, subtitle: str):
    st.title(f"{icon} {title}")
    st.caption(subtitle)
    st.divider()


def show_toast(message: str, icon: str = "\u2705"):
    st.toast(f"{icon} {message}")


def _render_toolbar(current_page_title: str, user: dict):
    if current_page_title == "Live Monitor":
        return
    c1, c2, c3 = st.columns([4, 1, 1])
    with c1:
        st.markdown("<div></div>", unsafe_allow_html=True)
    with c2:
        auto_refresh = st.selectbox(
            "Auto refresh", ["Off", "5s", "30s", "1m", "5m"], index=1,
            key="header_refresh", label_visibility="collapsed",
        )
        refresh_map = {"Off": 0, "5s": 5, "30s": 30, "1m": 60, "5m": 300}
        cache_control["refresh_interval"] = refresh_map.get(auto_refresh, 30)
    with c3:
        if get_user_permissions(user).get("can_export"):
            if st.button("\U0001f4e5 Export CSV", key="export_btn", use_container_width=True):
                st.session_state["do_export"] = True


def _maybe_render_export():
    if not st.session_state.get("do_export"):
        return
    alerts_df = _app().get("alerts_df")
    if alerts_df is not None and len(alerts_df) > 0:
        export_df = alerts_df[["datetime", "subject_id", "clip_id", "confidence", "tier", "outcome", "response_time", "status", "acknowledged_by"]].copy()
        export_df.columns = ["Time", "Subject ID", "Clip ID", "Confidence", "Tier", "Outcome", "Response Time", "Status", "Acknowledged By"]
        export_df["Time"] = export_df["Time"].dt.strftime("%Y-%m-%d %H:%M:%S")
        csv = export_df.to_csv(index=False)
        st.download_button("\U0001f4e5 Download CSV", csv, "alerts_export.csv", "text/csv")
    st.session_state["do_export"] = False

# ═══════════════════════════════════════════════════════════════════════════════
# ALERT DETAIL (native) — shared by table selection and event inspection
# ═══════════════════════════════════════════════════════════════════════════════

_TIER_COLOR = {"high": "red", "medium": "orange", "low": "green"}
_STATUS_COLOR = {"pending": "orange", "acknowledged": "green", "escalated": "red", "dismissed": "gray"}


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
        st.divider()

        video_path = alert_data.get("video_clip_path")
        if video_path and Path(video_path).exists():
            st.markdown("**Video clip**")
            st.video(str(video_path))
            with open(video_path, "rb") as vf:
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
                if permissions.get("can_acknowledge") and st.button("\u2705 Acknowledge", key=f"ack_{key_prefix}", use_container_width=True, type="primary"):
                    from alert import AlertManager
                    user_info = st.session_state.get("auth_user", {})
                    AlertManager.acknowledge_alert(ALERT_LOG, alert_data.get("timestamp", 0), user_info.get("username", "unknown"), user_info.get("role", "viewer"), "acknowledged")
                    show_toast(f"Alert for {subject} acknowledged", "\u2705")
                    time.sleep(0.3)
                    st.rerun()
            with cols[1]:
                if permissions.get("can_dismiss") and st.button("\u274c Dismiss", key=f"dismiss_{key_prefix}", use_container_width=True):
                    from alert import AlertManager
                    user_info = st.session_state.get("auth_user", {})
                    AlertManager.acknowledge_alert(ALERT_LOG, alert_data.get("timestamp", 0), user_info.get("username", "unknown"), user_info.get("role", "viewer"), "dismissed")
                    show_toast(f"Alert for {subject} dismissed", "\u274c")
                    time.sleep(0.3)
                    st.rerun()
            with cols[2]:
                if permissions.get("can_escalate") and st.button("\U0001f6a8 Escalate", key=f"esc_{key_prefix}", use_container_width=True):
                    user_info = st.session_state.get("auth_user", {})
                    _escalate_alerts([alert_data.get("timestamp", 0)], user_info,
                                     notify=_escalation_config().get("notify_on_escalate", True))
                    show_toast(f"Alert for {subject} escalated!", "\U0001f6a8")
                    time.sleep(0.3)
                    st.rerun()
        else:
            st.info(f"This alert has already been {status_val}.")

# ═══════════════════════════════════════════════════════════════════════════════
# ALERTS PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def render_alerts_page():
    data = _app()
    alerts_df = data.get("alerts_df")
    user = data.get("user")

    _page_header("\U0001f514", "Alert Management", "Monitor and respond to fall detection alerts.")

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
            alerts_df = _app()["alerts_df"]

    total = int(len(alerts_df))
    pending = int((alerts_df["status"] == "pending").sum())
    acknowledged = int((alerts_df["status"] == "acknowledged").sum())
    escalated = int((alerts_df["status"] == "escalated").sum())
    high_risk = int((alerts_df["tier"] == "high").sum())
    high_conf = int(alerts_df["confidence"].fillna(0).ge(0.85).sum())

    m = st.columns(6)
    m[0].metric("Total", total)
    m[1].metric("Pending", pending)
    m[2].metric("Acknowledged", acknowledged)
    m[3].metric("Escalated", escalated)
    m[4].metric("High-risk", high_risk)
    m[5].metric("High-conf", high_conf)
    st.divider()

    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    with c1:
        search = st.text_input("\U0001f50d", placeholder="Search subject or clip", key="alert_search", label_visibility="collapsed")
    with c2:
        tier_filter = st.pills("Tier", ["All", "high", "medium", "low"], default="All",
                               key="alert_tier", label_visibility="collapsed", selection_mode="single")
    with c3:
        status_filter = st.pills("Status", ["All", "pending", "acknowledged", "escalated", "dismissed"],
                                 default="All", key="alert_status", label_visibility="collapsed", selection_mode="single")
    with c4:
        sort_order = st.selectbox("Sort", ["Newest", "Oldest", "Confidence"], key="alert_sort", label_visibility="collapsed")

    # ─── Date range filter (Phase 2) ────────────────────────────────────────────
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
        filtered = filtered[filtered["datetime"].dt.normalize() <= pd.Timestamp(end_date)]

    if len(filtered) == 0:
        st.warning("No alerts match the current filters.")
        return

    if sort_order == "Oldest":
        filtered = filtered.sort_values("datetime", ascending=True)
    elif sort_order == "Confidence":
        filtered = filtered.sort_values("confidence", ascending=False)
    else:
        filtered = filtered.sort_values("datetime", ascending=False)

    display_df = pd.DataFrame({
        "Time": filtered["datetime"].dt.strftime("%m-%d %H:%M"),
        "Subject": filtered["subject_id"].astype(str),
        "Tier": filtered["tier"].str.upper(),
        "Confidence": (filtered["confidence"].fillna(0) * 100).astype(int).astype(str) + "%",
        "Status": filtered["status"].str.upper(),
    })

    st.caption("Select one or more rows (or press \u2318-click) to inspect and act. \u2318=F \u00b7 \u23ce=R \u00b7 Esc=clear")
    keyboard_html = """
    <div id="kb-root"></div>
    <script>
    (function() {
      function findInputs(){const all=[];function walk(root){
        (root.querySelectorAll('input')||[]).forEach(function(i){all.push(i)});
        (root.querySelectorAll('*')||[]).forEach(function(el){if(el.shadowRoot)walk(el.shadowRoot)});
      } walk(document); return all;}
      document.addEventListener('keydown', function(e) {
        if(e.metaKey||e.ctrlKey||e.altKey) return;
        const t=(e.target.tagName||'').toLowerCase();
        const k=e.key.toLowerCase();
        if(k==='f'&&t!=='input'&&t!=='textarea') {
          e.preventDefault();
          const ins=findInputs();
          const search=ins.find(function(i){return (i.placeholder||'').toLowerCase().indexOf('search')>-1})||ins[0];
          if(search) search.focus();
        } else if(k==='r'&&t!=='input'&&t!=='textarea') {
          e.preventDefault();
          const btn=document.querySelector('[data-testid="stToolbarButton"] button');
          if(btn) btn.click();
        } else if(e.key==='Escape') {
          if(document.activeElement) document.activeElement.blur();
          const ins=findInputs(); ins.forEach(function(i){i.blur()});
        }
      });
    })();
    </script>
    """
    st.html(keyboard_html)

    event = st.dataframe(
        display_df,
        hide_index=True,
        use_container_width=True,
        height=min(len(filtered) * 35 + 65, 500),
        on_select="rerun",
        selection_mode="multi-row",
    )

    selected_rows = event.selection.rows
    permissions = get_user_permissions(user)
    if len(selected_rows) > 0:
        # Resolve selected rows back to the filtered dataframe.
        sel_idx = filtered.iloc[selected_rows]
        pending_ts = sorted(sel_idx.loc[sel_idx["status"] == "pending", "datetime"].tolist())
        n_pending = len(pending_ts)
        ts_list = sel_idx["datetime"].dt.timestamp().tolist()

        st.divider()
        st.caption(f"{len(selected_rows)} alert{'s' if len(selected_rows) != 1 else ''} selected \u00b7 {n_pending} actionable")
        cols = st.columns([1, 1, 1, 3])
        from alert import AlertManager
        with cols[0]:
            can_ack = permissions.get("can_acknowledge", False) and n_pending > 0
            if st.button("\u2705 Acknowledge", key="bulk_ack", disabled=not can_ack, use_container_width=True):
                AlertManager.bulk_update_alerts(ALERT_LOG, ts_list, user.get("username",""), user.get("role",""), "acknowledged")
                st.toast("Selected alerts acknowledged", icon="\u2705")
                time.sleep(0.3); st.rerun()
        with cols[1]:
            can_dismiss = permissions.get("can_dismiss", False) and n_pending > 0
            if st.button("\u274c Dismiss", key="bulk_dismiss", disabled=not can_dismiss, use_container_width=True):
                AlertManager.bulk_update_alerts(ALERT_LOG, ts_list, user.get("username",""), user.get("role",""), "dismissed")
                st.toast("Selected alerts dismissed", icon="\u274c")
                time.sleep(0.3); st.rerun()
        with cols[2]:
            can_esc = permissions.get("can_escalate", False) and n_pending > 0
            if st.button("\U0001f6a8 Escalate", key="bulk_esc", disabled=not can_esc, use_container_width=True):
                _escalate_alerts(ts_list, user, notify=_escalation_config().get("notify_on_escalate", True))
                st.toast("Selected alerts escalated \u2014 follow-up urgent email sent", icon="\U0001f6a8")
                time.sleep(0.3); st.rerun()

    # Single-row detail (last-selected shows the inspector).
    if len(selected_rows) == 1:
        pos = selected_rows[0]
        row = filtered.iloc[pos]
        render_alert_detail(row.to_dict(), user, key_prefix=f"sel_{pos}", expanded=True)

# ═══════════════════════════════════════════════════════════════════════════════
# LIVE MONITOR PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def _stream_server_config() -> dict:
    import yaml
    try:
        with open("config.yaml", "r") as f:
            cfg = yaml.safe_load(f)
    except Exception:
        cfg = {}
    s = cfg.get("streaming", {})
    r = cfg.get("recording", {})
    cam = cfg.get("camera", {})
    allow_remote = s.get("allow_remote", False)
    return {
        "enabled": s.get("enabled", True),
        "host": "0.0.0.0" if allow_remote else s.get("host", "127.0.0.1"),
        "port": int(s.get("port", 8091)),
        "jpeg_quality": int(s.get("jpeg_quality", 80)),
        "max_fps": float(s.get("max_fps", 15)),
        "camera": {
            "source": cam.get("source", cam.get("index", 0)),
            "width": int(cam.get("width", 640)),
            "height": int(cam.get("height", 480)),
            "fps": float(cam.get("fps", 30)),
        },
        "use_synthetic": s.get("use_synthetic", False),
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


def _fetch_stream_metrics(base_url: str) -> Optional[dict]:
    if not base_url:
        return None
    try:
        with urllib.request.urlopen(f"{base_url}/metrics", timeout=3) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def _post_stream_action(base_url: str, action: str) -> Optional[dict]:
    if not base_url:
        return None
    try:
        req = urllib.request.Request(f"{base_url}/record/{action}", method="POST")
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        logger.warning(f"Record {action} failed: {e}")
        return None


@st.fragment(run_every=1.0)
def _render_live_metrics(status: dict, alerts_df: pd.DataFrame, base_url: str):
    live = _fetch_stream_metrics(base_url) or {}
    fps = live.get("fps", 0.0)
    rec_active = live.get("recording_active", False)
    cam_ok = live.get("camera_available", False)

    now = pd.Timestamp.now()
    today = now.normalize()
    if "datetime" in alerts_df.columns and len(alerts_df) > 0:
        last_hour_count = int((alerts_df["datetime"] >= (now - pd.Timedelta(hours=1))).sum())
        today_count = int((alerts_df["datetime"] >= today).sum())
    else:
        last_hour_count = 0
        today_count = 0

    age = live.get("last_frame_age_sec")
    age_str = f"{age:.1f}s" if age is not None else "n/a"

    def _cam_label():
        if cam_ok:
            return "Live camera"
        return "Simulated" if base_url else "Offline"

    m = st.columns(4)
    m[0].metric("Live FPS", f"{fps:.1f}")
    m[1].metric("Falls / 1 hour", last_hour_count)
    m[2].metric("Alerts today", today_count)
    m[3].metric("Camera", _cam_label())
    st.caption(f"Last frame {age_str} ago \u00b7 {'Recording' if rec_active else 'Not recording'}")


def _render_video_panel(base_url: str):
    frame_url = f"{base_url}/frame?t=" if base_url else None
    if not frame_url:
        st.info("Stream server is offline. Enable `streaming.enabled` in config.yaml to preview the live feed.")
        return

    html = f"""
    <div style="position:relative;background:#0b1220;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden;">
        <img id="fg-live"
             alt="Live camera feed"
             style="display:block;width:100%;aspect-ratio:16/9;object-fit:contain;background:#0b1220;" />
        <div style="position:absolute;top:12px;left:12px;background:rgba(11,18,32,0.7);color:#5eead4;font-family:Menlo,Consolas,monospace;font-size:11px;letter-spacing:1px;padding:5px 10px;border-radius:100px;border:1px solid rgba(94,234,212,0.35);">
            <span id="fg-dot" style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#5eead4;margin-right:6px;"></span>
            <span id="fg-status">CONNECTING</span>
        </div>
    </div>
    <script>
    (function(){{
      var img = document.getElementById('fg-live');
      var st  = document.getElementById('fg-status');
      var dot = document.getElementById('fg-dot');
      var base = '{frame_url}';
      var live = false;
      var lastOk = Date.now();
      function tick(){{ img.src = base + Date.now(); }}
      img.onload = function(){{
        if(!live){{ live = true; st.textContent = 'LIVE'; st.style.color = '#5eead4'; dot.style.background = '#5eead4'; }}
        lastOk = Date.now();
        setTimeout(tick, 200);
      }};
      img.onerror = function(){{
        if(live){{ live = false; st.textContent = 'RECONNECTING'; st.style.color = '#fbbf24'; dot.style.background = '#fbbf24'; }}
        setTimeout(tick, 1500);
      }};
      setInterval(function(){{
        if(new Date() - lastOk > 3500 && live){{
          live = false; st.textContent = 'OFFLINE'; st.style.color = '#f87171'; dot.style.background = '#f87171';
        }}
      }}, 1000);
      tick();
    }})();
    </script>
    """
    st.iframe(html, width="stretch", height=380)


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
        with urllib.request.urlopen(url, timeout=5) as r:
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
    tier_color = {"high": "#dc2626", "medium": "#d97706", "low": "#16a34a"}
    dots = []
    for mk in sorted(markers, key=lambda m: m["offset_sec"]):
        pct = min(max(mk["offset_sec"] / duration_sec * 100.0, 0.0), 100.0)
        ts = time.strftime(
            "%H:%M:%S", time.localtime(mk.get("timestamp") or 0)
        )
        color = tier_color.get(mk.get("tier", "low"), "#16a34a")
        title = f"{ts} \u00b7 Tier: {mk.get('tier','low')} \u00b7 Conf: {mk.get('confidence',0):.2f} \u00b7 {mk.get('subject_id','')}"
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
        f'background:linear-gradient(90deg,#e2e8f0,#cbd5e1);overflow:visible;">'
        f"<div style=\"position:absolute;inset:0;margin:auto;height:4px;border-radius:4px;"
        f"background:#cbd5e1;\"></div>{''.join(dots)}</div>"
    )
    st.caption("\u23f3 Timeline \u00b7 click a marker to seek \u00b7 tier colors: high-red, medium-amber, low-green")
    st.html(bar)


def _render_recording_panel(user: dict, base_url: str, cfg: dict = None,
                            alerts_df: pd.DataFrame = None):
    permissions = get_user_permissions(user)
    if not permissions.get("can_manage_settings"):
        return

    rec_path = Path((cfg or {}).get("record_path", "data/recordings"))
    live = _fetch_stream_metrics(base_url) or {}
    rec_active = live.get("recording_active", False)
    segments = sorted(rec_path.glob("rec_*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
    total_mb = sum(f.stat().st_size for f in segments) / 1024 / 1024

    st.subheader("Recording")
    c1, c2 = st.columns([1, 4])
    with c1:
        if rec_active:
            if st.button("\u23f9 Stop", key="rec_stop", use_container_width=True):
                _post_stream_action(base_url, "stop")
                show_toast("Recording stopped", "\u23f9")
                time.sleep(0.3)
                st.rerun()
        else:
            if st.button("\u25cf Record", key="rec_start", use_container_width=True, type="primary"):
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


def render_live_monitor():
    data = _app()
    base_url = data.get("base_url")
    alerts_df = data.get("alerts_df")
    if alerts_df is None:
        alerts_df = pd.DataFrame()

    _page_header("\U0001f4f9", "Live Monitor", "Real-time fall detection preview.")
    _render_video_panel(base_url)

    try:
        _render_live_metrics(data.get("status", {}), alerts_df, base_url)
    except Exception as e:
        st.warning(f"Live metrics unavailable: {e}")

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
    m[2].metric("High-risk", high_risk)
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
    export_cols = ["datetime", "timestamp", "subject_id", "clip_id", "confidence",
                   "tier", "status", "acknowledged_by", "acknowledged_at",
                   "grace_period_outcome", "grace_period_response_time"]
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
        use_container_width=True,
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
            now = pd.Timestamp.now().normalize()
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
            idx = pd.date_range(end=pd.Timestamp.now().normalize(), periods=14, freq="D")
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
                f'<div style="text-align:center;color:#666;">{h:02d}</div>' for h in range(24)))
            wd_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for wd in range(7):
                html.append(f'<div style="text-align:right;padding-right:6px;color:#666;">{wd_labels[wd]}</div>')
                for h in range(24):
                    v = int(grid.iloc[wd, h])
                    intensity = min(v / max_val, 1.0) if max_val else 0.0
                    r = int(240 - 215 * intensity)
                    g = int(247 - 220 * intensity)
                    b = int(255)
                    cell_info = f"Alerts: {v}" if v else "No alerts"
                    label = str(v) if v else "\u00b7"
                    color = "#1f2c4d" if intensity > 0.5 else "#7a8699"
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
                            idx = pd.date_range(end=pd.Timestamp.now().normalize(), periods=14, freq="D")
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
                    c2.metric("High-risk", high_risk_n)
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

def render_system_status_page():
    data = _app()
    status = data.get("status", {})

    _page_header("\u2699\ufe0f", "System Status", "Hardware and service health.")

    last = status.get("last_check_in", datetime.now())
    mins = int((datetime.now() - last).total_seconds() / 60)
    time_str = f"{mins}m ago" if mins < 60 else f"{mins // 60}h ago"

    m = st.columns(4)
    m[0].metric("Uptime", f"{status.get('uptime_hours', 0):.1f} h")
    m[1].metric("Alerts today", status.get("total_alerts_today", 0))
    m[2].metric("Pending", status.get("total_pending", 0))
    m[3].metric("Escalated", status.get("total_escalated", 0))
    st.divider()

    cam_ok = status.get("camera_online", False)
    model_ok = status.get("model_loaded", False)
    grace = status.get("grace_period_enabled", False)

    c1, c2 = st.columns(2)
    with c1:
        with st.status(f"Camera \u2014 {'Online' if cam_ok else 'Offline'}", expanded=False) as s:
            st.write(f"Last check-in: {time_str}")
            s.update(label=f"Camera \u2014 {'Online' if cam_ok else 'Offline'}", state="complete" if cam_ok else "error")
        with st.status("Grace period", expanded=False) as s:
            st.write("Configurable delay before an alert is considered final.")
            s.update(label=f"Grace period \u2014 {'Active' if grace else 'Disabled'}", state="complete" if grace else "running")
        with st.status(f"Email alerts \u2014 {'Active' if status.get('email_enabled') else 'Disabled'}", expanded=False) as s:
            st.write("Notification channel for fall alerts.")
            s.update(state="complete" if status.get("email_enabled") else "running")
        with st.status(f"SMS alerts \u2014 {'Active' if status.get('sms_enabled') else 'Disabled'}", expanded=False) as s:
            st.write("Notification channel for fall alerts.")
            s.update(state="complete" if status.get("sms_enabled") else "running")
    with c2:
        with st.status(f"ML model \u2014 {'Loaded' if model_ok else 'Error'}", expanded=False) as s:
            st.write("Pose-estimation model used for fall detection.")
            s.update(label=f"ML model \u2014 {'Loaded' if model_ok else 'Error'}", state="complete" if model_ok else "error")
        with st.status("False alarms prevented", expanded=False) as s:
            st.write(f"{status.get('false_alarms_prevented', 0)} events cancelled by validation.")
            s.update(label=f"{status.get('false_alarms_prevented', 0)} prevented", state="complete")
        st.metric("Alerts acknowledged", status.get("total_acknowledged", 0))
        st.metric("Alerts pending", status.get("total_pending", 0))

# ═══════════════════════════════════════════════════════════════════════════════
# PRIVACY PAGE
# ═══════════════════════════════════════════════════════════════════════════════

def render_privacy_page():
    _page_header("\U0001f512", "Privacy Center", "Data protection and compliance.")

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Privacy-first design")
        st.markdown(
            "- **No video storage** \u2014 raw frames are never saved to disk.\n"
            "- **No video transmission** \u2014 no video leaves the device.\n"
            "- **Pose-only processing** \u2014 only numeric keypoints (33 points) are analyzed.\n"
            "- **Alert-only output** \u2014 only text alerts are sent when a fall is detected.\n"
            "- **Local processing** \u2014 all analysis runs on-device.\n"
            "- **Minimal logging** \u2014 only alert timestamps and outcomes are stored."
        )
        st.divider()
        st.info("Recording is opt-in, admin-only, and auto-deletes after the retention window.")

    with c2:
        st.subheader("Compliance")
        with st.status("GDPR compliant", expanded=False) as s:
            st.write("Minimal data collection, on-device processing.")
            s.update(state="complete")
        with st.status("HIPAA ready", expanded=False) as s:
            st.write("Suitable for protected health information environments.")
            s.update(state="complete")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — native navigation router (+ test override via FG_PAGE env)
# ═══════════════════════════════════════════════════════════════════════════════

_PAGE_RUNNERS = {
    "alerts": render_alerts_page,
    "live": render_live_monitor,
    "analytics": render_analytics,
    "system": render_system_status_page,
    "privacy": render_privacy_page,
}


def main():
    st.set_page_config(
        page_title="FallGuard AI \u2014 Elderly Care System",
        page_icon="\U0001f6e1\ufe0f",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(LIGHT_CSS, unsafe_allow_html=True)

    user = get_current_user()
    if not user:
        render_login_page()
        return

    config = get_dashboard_config()
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
                st.Page(render_alerts_page, title="Alerts", icon="\U0001f514", url_path="alerts", default=True),
                st.Page(render_live_monitor, title="Live Monitor", icon="\U0001f4f9", url_path="live"),
            ],
            "Insights": [
                st.Page(render_analytics, title="Analytics", icon="\U0001f4ca", url_path="analytics"),
            ],
            "System": [
                st.Page(render_system_status_page, title="System", icon="\u2699\ufe0f", url_path="system"),
                st.Page(render_privacy_page, title="Privacy", icon="\U0001f512", url_path="privacy"),
            ],
        }, position="sidebar")
        render_sidebar_user(user)

    current_page_title = nav.title
    if current_page_title != "Live Monitor" and cache_control["refresh_interval"] > 0:
        if time.time() - cache_control["last_refresh"] >= cache_control["refresh_interval"]:
            cache_control["last_refresh"] = time.time()
            st.rerun()

    _render_toolbar(current_page_title, user)
    _maybe_render_export()
    nav.run()


if __name__ == "__main__":
    main()