"""be2 schema: users auth subjects devices events alerts notifications feedback models audit

Revision ID: 2edc787b3ea7
Revises: 16b5a4f492ee
Create Date: 2026-09-24 17:45:44.835936

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2edc787b3ea7'
down_revision: Union[str, Sequence[str], None] = '16b5a4f492ee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.execute(
        """
        CREATE TABLE users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email citext UNIQUE NOT NULL,
            name text NOT NULL,
            password_hash text NOT NULL,
            role text NOT NULL CHECK (role IN ('admin', 'caregiver', 'ml_engineer', 'operator')),
            status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
            must_change_password boolean NOT NULL DEFAULT false,
            notify_email boolean NOT NULL DEFAULT true,
            last_login_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE refresh_tokens (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash text NOT NULL,
            expires_at timestamptz NOT NULL,
            revoked_at timestamptz,
            replaced_by uuid REFERENCES refresh_tokens(id),
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id)")

    op.execute(
        """
        CREATE TABLE subjects (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            display_name text NOT NULL,
            location_label text,
            status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE caregiver_assignments (
            user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            subject_id uuid NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, subject_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE devices (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            device_name text UNIQUE NOT NULL,
            device_type text,
            location text,
            status text NOT NULL DEFAULT 'registered' CHECK (status IN ('registered', 'active', 'revoked')),
            subject_id uuid REFERENCES subjects(id),
            api_key_hash text,
            api_key_prefix text,
            key_rotated_at timestamptz,
            last_seen_at timestamptz,
            software_version text,
            model_version text,
            health_state text NOT NULL DEFAULT 'UNKNOWN'
                CHECK (health_state IN ('HEALTHY', 'DEGRADED', 'OFFLINE', 'ERROR', 'UNKNOWN')),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            revoked_at timestamptz
        )
        """
    )

    op.execute(
        """
        CREATE TABLE cameras (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            device_id uuid NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
            name text,
            source_type text CHECK (source_type IN ('webcam', 'usb', 'csi', 'rtsp', 'file')),
            resolution text,
            fps real,
            status text,
            last_frame_at timestamptz
        )
        """
    )

    op.execute(
        """
        CREATE TABLE device_health_snapshots (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            device_id uuid NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
            recorded_at timestamptz NOT NULL DEFAULT now(),
            camera_status text,
            camera_fps real,
            last_frame_at timestamptz,
            inference_latency_ms integer,
            model_loaded boolean,
            cpu_pct real,
            mem_pct real,
            temperature_c real,
            queue_depth integer,
            backend_connectivity text,
            software_version text,
            model_version text,
            computed_state text
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_device_health_snapshots_device_recorded "
        "ON device_health_snapshots (device_id, recorded_at DESC)"
    )

    op.execute(
        """
        CREATE TABLE events (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            client_event_id uuid NOT NULL,
            device_id uuid NOT NULL REFERENCES devices(id),
            subject_id uuid REFERENCES subjects(id),
            track_id integer,
            event_type text NOT NULL DEFAULT 'possible_fall',
            state text NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING', 'CANCELLED', 'CONFIRMED')),
            detected_at timestamptz NOT NULL,
            received_at timestamptz NOT NULL DEFAULT now(),
            grace_seconds integer NOT NULL DEFAULT 20,
            grace_deadline timestamptz NOT NULL,
            resolved_at timestamptz,
            resolved_by text CHECK (resolved_by IN ('edge', 'caregiver', 'backend_timeout')),
            confidence real,
            confidence_calibrated boolean NOT NULL DEFAULT false,
            tier text CHECK (tier IN ('low', 'medium', 'high')),
            model_version text,
            feature_version text,
            pose_quality real,
            legacy boolean NOT NULL DEFAULT false,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (device_id, client_event_id)
        )
        """
    )
    op.execute("CREATE INDEX ix_events_detected_at ON events (detected_at DESC)")
    op.execute("CREATE INDEX ix_events_subject_detected ON events (subject_id, detected_at DESC)")
    op.execute("CREATE INDEX ix_events_state ON events (state)")

    op.execute(
        """
        CREATE TABLE event_evidence (
            event_id uuid PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
            rapid_motion boolean,
            orientation_change real,
            body_height_change real,
            post_event_stillness boolean,
            pose_quality real,
            evidence_summary text,
            extra jsonb
        )
        """
    )

    op.execute(
        """
        CREATE TABLE alerts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            event_id uuid UNIQUE NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            status text NOT NULL DEFAULT 'OPEN'
                CHECK (status IN ('OPEN', 'ACKNOWLEDGED', 'DISMISSED', 'ESCALATED')),
            notification_status text NOT NULL DEFAULT 'PENDING'
                CHECK (notification_status IN ('PENDING', 'SENT', 'FAILED')),
            created_at timestamptz NOT NULL DEFAULT now(),
            acknowledged_by uuid REFERENCES users(id),
            acknowledged_at timestamptz,
            dismissed_by uuid REFERENCES users(id),
            dismissed_at timestamptz,
            escalated_by uuid REFERENCES users(id),
            escalated_at timestamptz,
            escalation_reason text CHECK (escalation_reason IN ('manual', 'auto_timeout', 'notification_failed'))
        )
        """
    )
    op.execute("CREATE INDEX ix_alerts_status_created ON alerts (status, created_at DESC)")

    op.execute(
        """
        CREATE TABLE alert_actions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            alert_id uuid NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
            user_id uuid REFERENCES users(id),
            action text NOT NULL,
            note text,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE notifications (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            alert_id uuid REFERENCES alerts(id) ON DELETE CASCADE,
            recipient_user_id uuid NOT NULL REFERENCES users(id),
            channel text NOT NULL DEFAULT 'email',
            provider text,
            kind text NOT NULL CHECK (kind IN ('fall_alert', 'escalation')),
            status text NOT NULL DEFAULT 'QUEUED'
                CHECK (status IN ('QUEUED', 'SENDING', 'SENT', 'FAILED')),
            attempt_count integer NOT NULL DEFAULT 0,
            next_attempt_at timestamptz,
            last_attempt_at timestamptz,
            error_code text,
            delivered_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_notifications_status_next_attempt ON notifications (status, next_attempt_at)")

    op.execute(
        """
        CREATE TABLE caregiver_feedback (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            event_id uuid NOT NULL REFERENCES events(id) ON DELETE CASCADE,
            caregiver_id uuid NOT NULL REFERENCES users(id),
            label text NOT NULL CHECK (label IN ('TRUE_FALL', 'FALSE_POSITIVE', 'UNCERTAIN', 'SYSTEM_FAILURE')),
            comment text,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (event_id, caregiver_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE model_versions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            model_name text NOT NULL,
            version text NOT NULL,
            model_type text CHECK (model_type IN ('random_forest', 'cnn_lstm', 'tcn', 'ensemble')),
            artifact_uri text,
            feature_version text,
            dataset_version text,
            metrics_json jsonb,
            release_gate jsonb,
            status text NOT NULL DEFAULT 'registered'
                CHECK (status IN ('registered', 'candidate', 'approved', 'production', 'retired')),
            created_by uuid REFERENCES users(id),
            created_at timestamptz NOT NULL DEFAULT now(),
            approved_by uuid REFERENCES users(id),
            approved_at timestamptz,
            UNIQUE (model_name, version)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE audit_logs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid REFERENCES users(id),
            device_id uuid REFERENCES devices(id),
            action text NOT NULL,
            resource_type text,
            resource_id text,
            result text NOT NULL CHECK (result IN ('success', 'failure')),
            request_id text,
            ip text,
            metadata jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at DESC)")


def downgrade() -> None:
    """Downgrade schema."""
    for table in (
        "audit_logs",
        "model_versions",
        "caregiver_feedback",
        "notifications",
        "alert_actions",
        "alerts",
        "event_evidence",
        "events",
        "device_health_snapshots",
        "cameras",
        "devices",
        "caregiver_assignments",
        "subjects",
        "refresh_tokens",
        "users",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    op.execute("DROP EXTENSION IF EXISTS citext")
