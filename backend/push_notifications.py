"""
Push notification helpers for per-job "notify when ready" subscriptions.

Storage:
- Supabase table public.job_ready_notifications when configured
- In-memory fallback for local/test environments

Delivery:
- FCM HTTP v1 using a service account credential
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from logger_config import setup_logging
from supabase_client import get_supabase_client, is_supabase_configured

logger = setup_logging()

_TABLE_NAME = "job_ready_notifications"
_FCM_SCOPE = ["https://www.googleapis.com/auth/firebase.messaging"]

_in_memory_notifications: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

_cached_fcm_signature: Optional[Tuple[str, str, str]] = None
_cached_fcm_credentials: Optional[service_account.Credentials] = None
_cached_fcm_project_id: Optional[str] = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_supabase_or_none():
    if not is_supabase_configured():
        return None
    try:
        return get_supabase_client()
    except Exception as e:
        logger.warning(f"Supabase unavailable for push notifications: {e}")
        return None


def register_job_ready_notification(
    *,
    job_id: str,
    project_id: str,
    user_id: str,
    device_token: str,
    platform: str,
) -> None:
    """Create or update a pending job-ready notification subscription."""
    token = (device_token or "").strip()
    if not token:
        raise ValueError("device_token must not be empty")

    normalized_platform = (platform or "").strip().lower()
    if normalized_platform not in ("ios", "android"):
        raise ValueError("platform must be either 'ios' or 'android'")

    now = _utc_now_iso()
    payload = {
        "job_id": job_id,
        "project_id": project_id,
        "user_id": user_id,
        "device_token": token,
        "platform": normalized_platform,
        "status": "pending",
        "requested_at": now,
        "sent_at": None,
        "last_error": None,
    }

    supabase = _get_supabase_or_none()
    if supabase:
        supabase.table(_TABLE_NAME).upsert(
            payload,
            on_conflict="job_id,user_id,device_token",
        ).execute()
        return

    key = (job_id, user_id, token)
    _in_memory_notifications[key] = {
        **_in_memory_notifications.get(key, {}),
        **payload,
    }


def get_pending_job_ready_notifications(job_id: str) -> List[Dict[str, Any]]:
    """Fetch pending subscriptions for a specific job."""
    supabase = _get_supabase_or_none()
    if supabase:
        result = (
            supabase.table(_TABLE_NAME)
            .select("*")
            .eq("job_id", job_id)
            .eq("status", "pending")
            .execute()
        )
        return list(result.data or [])

    return [
        dict(row)
        for row in _in_memory_notifications.values()
        if row.get("job_id") == job_id and row.get("status") == "pending"
    ]


def _mark_subscription_sent(row: Dict[str, Any]) -> None:
    now = _utc_now_iso()
    job_id = str(row.get("job_id") or "")
    user_id = str(row.get("user_id") or "")
    device_token = str(row.get("device_token") or "")
    row_id = row.get("id")

    supabase = _get_supabase_or_none()
    if supabase:
        query = supabase.table(_TABLE_NAME).update(
            {"status": "sent", "sent_at": now, "last_error": None}
        )
        if row_id:
            query = query.eq("id", row_id)
        else:
            query = query.eq("job_id", job_id).eq("user_id", user_id).eq(
                "device_token", device_token
            )
        query.execute()
        return

    key = (job_id, user_id, device_token)
    if key in _in_memory_notifications:
        _in_memory_notifications[key]["status"] = "sent"
        _in_memory_notifications[key]["sent_at"] = now
        _in_memory_notifications[key]["last_error"] = None


def _mark_subscription_failed(row: Dict[str, Any], error_message: str) -> None:
    job_id = str(row.get("job_id") or "")
    user_id = str(row.get("user_id") or "")
    device_token = str(row.get("device_token") or "")
    row_id = row.get("id")
    safe_error = (error_message or "Unknown push error")[:500]

    supabase = _get_supabase_or_none()
    if supabase:
        query = supabase.table(_TABLE_NAME).update(
            {"status": "failed", "last_error": safe_error}
        )
        if row_id:
            query = query.eq("id", row_id)
        else:
            query = query.eq("job_id", job_id).eq("user_id", user_id).eq(
                "device_token", device_token
            )
        query.execute()
        return

    key = (job_id, user_id, device_token)
    if key in _in_memory_notifications:
        _in_memory_notifications[key]["status"] = "failed"
        _in_memory_notifications[key]["last_error"] = safe_error


def _load_fcm_credentials() -> tuple[service_account.Credentials, str]:
    """Load and cache credentials needed for FCM HTTP v1 sends."""
    global _cached_fcm_signature
    global _cached_fcm_credentials
    global _cached_fcm_project_id

    project_id = (os.getenv("FCM_PROJECT_ID") or "").strip()
    raw_json = (os.getenv("FCM_SERVICE_ACCOUNT_JSON") or "").strip()
    json_file = (os.getenv("FCM_SERVICE_ACCOUNT_FILE") or "").strip()

    signature = (project_id, raw_json, json_file)
    if (
        _cached_fcm_credentials is not None
        and _cached_fcm_project_id
        and _cached_fcm_signature == signature
    ):
        return _cached_fcm_credentials, _cached_fcm_project_id

    if not project_id:
        raise RuntimeError("FCM_PROJECT_ID is not configured")

    if not raw_json and not json_file:
        raise RuntimeError(
            "FCM service account credentials are not configured. "
            "Set FCM_SERVICE_ACCOUNT_JSON or FCM_SERVICE_ACCOUNT_FILE."
        )

    if raw_json:
        try:
            info = json.loads(raw_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid FCM_SERVICE_ACCOUNT_JSON: {e}") from e
    else:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                info = json.load(f)
        except FileNotFoundError as e:
            raise RuntimeError(f"FCM service account file not found: {json_file}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in {json_file}: {e}") from e

    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=_FCM_SCOPE
    )

    _cached_fcm_signature = signature
    _cached_fcm_credentials = credentials
    _cached_fcm_project_id = project_id
    return credentials, project_id


def _get_fcm_access_token(credentials: service_account.Credentials) -> str:
    if not credentials.valid or credentials.expired or not credentials.token:
        credentials.refresh(GoogleAuthRequest())
    if not credentials.token:
        raise RuntimeError("Failed to obtain FCM access token")
    return credentials.token


def send_design_ready_push(
    *,
    device_token: str,
    platform: str,
    project_id: str,
    job_id: str,
) -> Dict[str, Any]:
    """Send a design-ready push notification through FCM HTTP v1."""
    credentials, fcm_project_id = _load_fcm_credentials()
    access_token = _get_fcm_access_token(credentials)

    message: Dict[str, Any] = {
        "token": device_token,
        "notification": {
            "title": "Your design is ready",
            "body": "Tap to view your Dream Space.",
        },
        "data": {
            "project_id": project_id,
            "job_id": job_id,
            "type": "design_ready",
        },
    }

    normalized_platform = platform.lower()
    if normalized_platform == "android":
        message["android"] = {"priority": "high"}
    elif normalized_platform == "ios":
        message["apns"] = {"headers": {"apns-priority": "10"}}

    endpoint = (
        f"https://fcm.googleapis.com/v1/projects/{fcm_project_id}/messages:send"
    )
    response = requests.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json={"message": message},
        timeout=12,
    )

    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(
            f"FCM send failed ({response.status_code}): {response.text[:300]}"
        )

    try:
        return response.json()
    except ValueError:
        return {"raw_response": response.text}


def dispatch_job_ready_notifications(job_id: str, project_id: str) -> Dict[str, int]:
    """
    Dispatch all pending job-ready notifications for the provided job.

    Returns a summary with total/sent/failed counts.
    """
    pending = get_pending_job_ready_notifications(job_id)
    if not pending:
        return {"total": 0, "sent": 0, "failed": 0}

    sent = 0
    failed = 0

    for row in pending:
        token = str(row.get("device_token") or "").strip()
        platform = str(row.get("platform") or "ios").strip().lower()
        if not token:
            _mark_subscription_failed(row, "Missing device token")
            failed += 1
            continue

        try:
            send_design_ready_push(
                device_token=token,
                platform=platform,
                project_id=project_id,
                job_id=job_id,
            )
            _mark_subscription_sent(row)
            sent += 1
        except Exception as e:
            logger.warning(
                f"Failed to send design-ready push for job={job_id} "
                f"user={row.get('user_id')}: {e}"
            )
            _mark_subscription_failed(row, str(e))
            failed += 1

    return {"total": len(pending), "sent": sent, "failed": failed}
