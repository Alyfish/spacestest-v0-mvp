"""
Background job manager with Supabase persistence and in-memory fallback.

Provides:
- Idempotent job creation (prevents duplicates from retries)
- Atomic claim/lock for restart safety
- Progress updates with phase descriptions
- Error handling with full traceback
- In-memory fallback when Supabase unavailable
"""

from __future__ import annotations

import os
import socket
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from logger_config import setup_logging

logger = setup_logging()


class JobType(str, Enum):
    GENERATE_IMAGE = "generate_image"
    INSPIRATION_REDESIGN = "inspiration_redesign"
    SEARCH_RECOMMENDATIONS = "search_recommendations"


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class JobInfo(BaseModel):
    """Job information model returned to clients."""

    id: str
    user_id: Optional[str] = None
    project_id: str
    job_type: str
    status: str
    progress_pct: int = 0
    phase: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class JobManager:
    """
    Manages background jobs with Supabase persistence.

    Features:
    - Idempotent job creation via idempotency_key
    - Atomic claim with lease (locked_at, locked_by)
    - Progress tracking with phases
    - In-memory fallback when Supabase unavailable
    """

    # Progress milestones for each job type
    PROGRESS_PHASES = {
        JobType.GENERATE_IMAGE: [
            (0, "Initializing"),
            (25, "Loading project context"),
            (50, "Generating image with AI"),
            (75, "Processing result"),
            (100, "Complete"),
        ],
        JobType.INSPIRATION_REDESIGN: [
            (0, "Initializing"),
            (20, "Loading inspiration context"),
            (40, "Preparing redesign prompt"),
            (60, "Generating redesigned image"),
            (80, "Processing result"),
            (100, "Complete"),
        ],
        JobType.SEARCH_RECOMMENDATIONS: [
            (0, "Initializing"),
            (20, "Analyzing recommendations"),
            (40, "Searching for products"),
            (70, "Filtering and ranking"),
            (90, "Finalizing results"),
            (100, "Complete"),
        ],
    }

    def __init__(self):
        self._supabase = None
        self._use_supabase = os.getenv("USE_SUPABASE_JOBS", "true").lower() == "true"
        self._in_memory_jobs: Dict[str, Dict] = {}
        self._worker_id = f"{socket.gethostname()}-{os.getpid()}"
        self._lease_seconds = int(os.getenv("JOB_LEASE_SECONDS", "300"))
        self._max_attempts = int(os.getenv("JOB_MAX_ATTEMPTS", "3"))

        if self._use_supabase:
            try:
                from supabase_client import get_supabase_client, is_supabase_configured

                if is_supabase_configured():
                    self._supabase = get_supabase_client()
                    logger.info("JobManager using Supabase storage")
                else:
                    logger.warning(
                        "Supabase not configured, using in-memory fallback"
                    )
            except Exception as e:
                logger.warning(f"Failed to init Supabase, using in-memory: {e}")

    @property
    def using_supabase(self) -> bool:
        """Check if Supabase is being used."""
        return self._supabase is not None

    async def create_job(
        self,
        project_id: str,
        job_type: JobType,
        user_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        request_data: Optional[Dict] = None,
    ) -> str:
        """
        Create a new job record.

        If idempotency_key is provided and a job with that key exists,
        returns the existing job_id instead of creating a duplicate.

        Args:
            project_id: Project this job belongs to
            job_type: Type of background task
            user_id: User who initiated the job
            idempotency_key: Optional key to prevent duplicate jobs
            request_data: Optional request context to store

        Returns:
            job_id: UUID of the created (or existing) job
        """
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        if self._supabase:
            try:
                # Check for existing job with same idempotency key
                if idempotency_key:
                    existing = (
                        self._supabase.table("jobs")
                        .select("id")
                        .eq("project_id", project_id)
                        .eq("job_type", job_type.value)
                        .eq("idempotency_key", idempotency_key)
                    )
                    if user_id:
                        existing = existing.eq("user_id", user_id)
                    result = existing.execute()

                    if result.data:
                        existing_id = result.data[0]["id"]
                        logger.info(
                            f"Returning existing job {existing_id} for idempotency_key={idempotency_key}"
                        )
                        return existing_id

                # Create new job
                job_data = {
                    "id": job_id,
                    "project_id": project_id,
                    "job_type": job_type.value,
                    "status": JobStatus.QUEUED.value,
                    "progress_pct": 0,
                    "phase": "Queued",
                    "attempts": 0,
                    "idempotency_key": idempotency_key,
                    "request": request_data,
                }
                if user_id:
                    job_data["user_id"] = user_id

                self._supabase.table("jobs").insert(job_data).execute()
                logger.info(
                    f"Created job {job_id}",
                    extra={
                        "job_id": job_id,
                        "job_type": job_type.value,
                        "project_id": project_id,
                    },
                )
                return job_id

            except Exception as e:
                logger.warning(f"Supabase insert failed, falling back to memory: {e}")

        # In-memory fallback
        if idempotency_key:
            for jid, job in self._in_memory_jobs.items():
                if (
                    job["project_id"] == project_id
                    and job["job_type"] == job_type.value
                    and job.get("idempotency_key") == idempotency_key
                ):
                    return jid

        self._in_memory_jobs[job_id] = {
            "id": job_id,
            "user_id": user_id,
            "project_id": project_id,
            "job_type": job_type.value,
            "status": JobStatus.QUEUED.value,
            "progress_pct": 0,
            "phase": "Queued",
            "attempts": 0,
            "idempotency_key": idempotency_key,
            "request": request_data,
            "result": None,
            "error": None,
            "error_code": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        return job_id

    async def claim_job(self, job_id: str) -> bool:
        """
        Atomically claim a job for processing.

        Sets status to 'processing', locked_at, locked_by, increments attempts.
        Only succeeds if job is in 'queued' status.

        Returns:
            True if claimed successfully, False if already claimed/cancelled
        """
        now = datetime.now(timezone.utc)

        if self._supabase:
            try:
                result = (
                    self._supabase.table("jobs")
                    .update(
                        {
                            "status": JobStatus.PROCESSING.value,
                            "locked_at": now.isoformat(),
                            "locked_by": self._worker_id,
                            "started_at": now.isoformat(),
                            "attempts": self._supabase.rpc(
                                "increment_attempts", {"row_id": job_id}
                            )
                            if False
                            else 1,  # Increment handled below
                        }
                    )
                    .eq("id", job_id)
                    .eq("status", JobStatus.QUEUED.value)
                    .execute()
                )

                # If no rows updated, job was already claimed or cancelled
                if not result.data:
                    logger.warning(f"Failed to claim job {job_id} - not in queued state")
                    return False

                # Increment attempts separately (simpler than RPC)
                self._supabase.table("jobs").update(
                    {"attempts": result.data[0].get("attempts", 0) + 1}
                ).eq("id", job_id).execute()

                logger.info(f"Claimed job {job_id}", extra={"job_id": job_id})
                return True

            except Exception as e:
                logger.error(f"Failed to claim job {job_id}: {e}")
                return False

        # In-memory fallback
        job = self._in_memory_jobs.get(job_id)
        if not job or job["status"] != JobStatus.QUEUED.value:
            return False

        job["status"] = JobStatus.PROCESSING.value
        job["locked_at"] = now.isoformat()
        job["locked_by"] = self._worker_id
        job["started_at"] = now.isoformat()
        job["attempts"] = job.get("attempts", 0) + 1
        job["updated_at"] = now.isoformat()
        return True

    async def update_progress(
        self,
        job_id: str,
        progress_pct: int,
        phase: Optional[str] = None,
    ):
        """Update job progress percentage and phase."""
        if self._supabase:
            try:
                update_data = {
                    "progress_pct": progress_pct,
                    "status": JobStatus.PROCESSING.value,
                }
                if phase:
                    update_data["phase"] = phase

                self._supabase.table("jobs").update(update_data).eq(
                    "id", job_id
                ).execute()

            except Exception as e:
                logger.warning(f"Failed to update progress for {job_id}: {e}")

        # In-memory fallback
        job = self._in_memory_jobs.get(job_id)
        if job:
            job["progress_pct"] = progress_pct
            job["status"] = JobStatus.PROCESSING.value
            if phase:
                job["phase"] = phase
            job["updated_at"] = datetime.now(timezone.utc).isoformat()

    async def complete_job(
        self,
        job_id: str,
        result: Dict[str, Any],
    ):
        """Mark job as complete with result."""
        now = datetime.now(timezone.utc)

        if self._supabase:
            try:
                self._supabase.table("jobs").update(
                    {
                        "status": JobStatus.DONE.value,
                        "progress_pct": 100,
                        "phase": "Complete",
                        "result": result,
                        "finished_at": now.isoformat(),
                    }
                ).eq("id", job_id).execute()

                logger.info(f"Job {job_id} completed", extra={"job_id": job_id})

            except Exception as e:
                logger.error(f"Failed to complete job {job_id}: {e}")

        # In-memory fallback
        job = self._in_memory_jobs.get(job_id)
        if job:
            job["status"] = JobStatus.DONE.value
            job["progress_pct"] = 100
            job["phase"] = "Complete"
            job["result"] = result
            job["finished_at"] = now.isoformat()
            job["updated_at"] = now.isoformat()

    async def fail_job(
        self,
        job_id: str,
        error: str,
        error_code: Optional[str] = None,
        error_trace: Optional[str] = None,
    ):
        """Mark job as failed with error details."""
        now = datetime.now(timezone.utc)

        if self._supabase:
            try:
                self._supabase.table("jobs").update(
                    {
                        "status": JobStatus.ERROR.value,
                        "error": error,
                        "error_code": error_code,
                        "error_trace": error_trace,
                        "finished_at": now.isoformat(),
                    }
                ).eq("id", job_id).execute()

                logger.error(
                    f"Job {job_id} failed: {error}",
                    extra={"job_id": job_id, "error_code": error_code},
                )

            except Exception as e:
                logger.error(f"Failed to mark job {job_id} as error: {e}")

        # In-memory fallback
        job = self._in_memory_jobs.get(job_id)
        if job:
            job["status"] = JobStatus.ERROR.value
            job["error"] = error
            job["error_code"] = error_code
            job["error_trace"] = error_trace
            job["finished_at"] = now.isoformat()
            job["updated_at"] = now.isoformat()

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job if it's still queued or processing.

        Returns:
            True if cancelled, False if already done/error/cancelled
        """
        now = datetime.now(timezone.utc)

        if self._supabase:
            try:
                result = (
                    self._supabase.table("jobs")
                    .update(
                        {
                            "status": JobStatus.CANCELLED.value,
                            "finished_at": now.isoformat(),
                        }
                    )
                    .eq("id", job_id)
                    .in_("status", [JobStatus.QUEUED.value, JobStatus.PROCESSING.value])
                    .execute()
                )

                cancelled = len(result.data) > 0
                if cancelled:
                    logger.info(f"Job {job_id} cancelled", extra={"job_id": job_id})
                return cancelled

            except Exception as e:
                logger.error(f"Failed to cancel job {job_id}: {e}")
                return False

        # In-memory fallback
        job = self._in_memory_jobs.get(job_id)
        if job and job["status"] in (
            JobStatus.QUEUED.value,
            JobStatus.PROCESSING.value,
        ):
            job["status"] = JobStatus.CANCELLED.value
            job["finished_at"] = now.isoformat()
            job["updated_at"] = now.isoformat()
            return True
        return False

    async def is_cancelled(self, job_id: str) -> bool:
        """Check if job has been cancelled (for early exit in executors)."""
        job = await self.get_job(job_id)
        return job is not None and job.status == JobStatus.CANCELLED.value

    async def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Get job details by ID."""
        if self._supabase:
            try:
                result = (
                    self._supabase.table("jobs")
                    .select("*")
                    .eq("id", job_id)
                    .execute()
                )

                if result.data:
                    data = result.data[0]
                    return JobInfo(
                        id=data["id"],
                        user_id=data.get("user_id"),
                        project_id=data["project_id"],
                        job_type=data["job_type"],
                        status=data["status"],
                        progress_pct=data.get("progress_pct", 0),
                        phase=data.get("phase"),
                        result=data.get("result"),
                        error=data.get("error"),
                        error_code=data.get("error_code"),
                        created_at=data.get("created_at"),
                        updated_at=data.get("updated_at"),
                    )
                return None

            except Exception as e:
                logger.error(f"Failed to get job {job_id}: {e}")

        # In-memory fallback
        job = self._in_memory_jobs.get(job_id)
        if job:
            return JobInfo(**job)
        return None

    async def get_project_jobs(
        self,
        project_id: str,
        user_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[JobInfo]:
        """Get all jobs for a project."""
        if self._supabase:
            try:
                query = (
                    self._supabase.table("jobs")
                    .select("*")
                    .eq("project_id", project_id)
                )

                if user_id:
                    query = query.eq("user_id", user_id)

                result = query.order("created_at", desc=True).limit(limit).execute()

                return [
                    JobInfo(
                        id=j["id"],
                        user_id=j.get("user_id"),
                        project_id=j["project_id"],
                        job_type=j["job_type"],
                        status=j["status"],
                        progress_pct=j.get("progress_pct", 0),
                        phase=j.get("phase"),
                        result=j.get("result"),
                        error=j.get("error"),
                        error_code=j.get("error_code"),
                        created_at=j.get("created_at"),
                        updated_at=j.get("updated_at"),
                    )
                    for j in result.data
                ]

            except Exception as e:
                logger.error(f"Failed to get jobs for project {project_id}: {e}")

        # In-memory fallback
        return [
            JobInfo(**j)
            for j in self._in_memory_jobs.values()
            if j["project_id"] == project_id
        ][:limit]

    def get_phase_for_progress(
        self, job_type: JobType, progress: int
    ) -> str:
        """Get the appropriate phase name for a progress level."""
        phases = self.PROGRESS_PHASES.get(job_type, [])
        phase = "Processing"
        for pct, phase_name in phases:
            if progress >= pct:
                phase = phase_name
        return phase


# Singleton instance
job_manager = JobManager()
