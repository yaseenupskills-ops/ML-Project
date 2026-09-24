from fastapi import FastAPI
import json

app = FastAPI(title="FallGuard", version="1.0", openapi_url="/openapi.json")

# Add some basic models to generate schemas
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class AuthLoginData(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    must_change_password: bool
    assigned_subject_ids: List[str]

class AnalyticsSummary(BaseModel):
    total_events: int
    confirmed: int
    cancelled: int
    alerts_open: int
    alerts_acknowledged: int
    alerts_dismissed: int
    alerts_escalated: int
    response_time_avg_s: float
    response_time_median_s: float
    response_time_p95_s: float
    notification_failures: int
    false_positive_feedback_count: int

class DeviceHealth(BaseModel):
    state: str
    camera_status: str
    model_loaded: bool
    last_seen_at: datetime

class SubjectInfo(BaseModel):
    id: str
    display_name: str
    location_label: str

class DeviceInfo(BaseModel):
    id: str
    device_name: str

class Evidence(BaseModel):
    rapid_motion: bool
    orientation_change: float
    body_height_change: float
    post_event_stillness: bool
    evidence_summary: str

class Alert(BaseModel):
    id: str
    status: str
    notification_status: str
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    response_time_s: Optional[float]

class Notification(BaseModel):
    channel: str
    kind: str
    status: str
    attempt_count: int
    last_attempt_at: Optional[datetime]
    error_code: Optional[str]

class Feedback(BaseModel):
    caregiver_id: str
    label: str
    comment: Optional[str]
    created_at: datetime

class TimelineEvent(BaseModel):
    at: datetime
    actor: str
    action: str
    note: Optional[str]

class Event(BaseModel):
    id: str
    state: str
    detected_at: datetime
    grace_deadline: datetime
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    subject: SubjectInfo
    device: DeviceInfo
    confidence: float
    confidence_calibrated: bool
    tier: str
    track_id: int
    model_version: str
    feature_version: str
    pose_quality: float
    evidence: Evidence
    alert: Optional[Alert]
    notifications: List[Notification]
    feedback: List[Feedback]
    timeline: List[TimelineEvent]
    server_time: datetime

class PaginatedEvents(BaseModel):
    items: List[Event]
    total: int
    server_time: datetime

class PaginatedAlerts(BaseModel):
    items: List[Event] # simplified for now
    total: int
    server_time: datetime

@app.post("/api/v1/auth/login")
def login(data: AuthLoginData): pass

@app.post("/api/v1/auth/refresh")
def refresh(): pass

@app.post("/api/v1/auth/logout")
def logout(): pass

@app.get("/api/v1/auth/me", response_model=UserResponse)
def get_me(): pass

@app.get("/api/v1/analytics/summary", response_model=AnalyticsSummary)
def get_analytics_summary(): pass

@app.get("/api/v1/events", response_model=PaginatedEvents)
def get_events(state: Optional[str] = None): pass

@app.get("/api/v1/events/{id}", response_model=Event)
def get_event(id: str): pass

@app.get("/api/v1/alerts", response_model=PaginatedAlerts)
def get_alerts(status: Optional[str] = None): pass

if __name__ == "__main__":
    openapi_schema = app.openapi()
    with open("openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)
