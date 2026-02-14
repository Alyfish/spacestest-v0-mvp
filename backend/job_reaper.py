"""
Job reaper for cleaning up stale and expired jobs.

Runs periodically to:
1. Requeue stale processing jobs (stuck after restart)
2. Mark max-attempts jobs as failed
3. Delete expired completed jobs
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from logger_config import setup_logging

logger = setup_logging()


class JobReaper:
    """
    Periodic job cleanup and recovery.

    Handles:
    - Stale jobs: processing but lease expired → requeue
    - Max attempts: too many retries → mark as error
    - Expired jobs: old completed jobs → delete
    """

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._lease_seconds = int(os.getenv("JOB_LEASE_SECONDS", "300"))
        self._max_attempts = int(os.getenv("JOB_MAX_ATTEMPTS", "3"))
        self._reap_interval = int(os.getenv("JOB_REAP_INTERVAL", "60"))  # seconds
        self._supabase = None

    def _get_supabase(self):
        """Lazy load Supabase client."""
        if self._supabase is None:
            try:
                from supabase_client import get_supabase_client, is_supabase_configured

                if is_supabase_configured():
                    self._supabase = get_supabase_client()
            except Exception as e:
                logger.warning(f"Reaper: Supabase not available: {e}")
        return self._supabase

    async def start(self):
        """Start the reaper background task."""
        if self._running:
            logger.warning("Reaper already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Job reaper started")

    async def stop(self):
        """Stop the reaper background task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Job reaper stopped")

    async def _run_loop(self):
        """Main reaper loop."""
        # Run immediately on startup
        await self._reap()

        while self._running:
            try:
                await asyncio.sleep(self._reap_interval)
                if self._running:
                    await self._reap()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reaper error: {e}")
                await asyncio.sleep(10)  # Back off on error

    async def _reap(self):
        """Execute one reap cycle."""
        supabase = self._get_supabase()
        if not supabase:
            return

        try:
            # Call the database functions
            requeued = await self._requeue_stale_jobs(supabase)
            deleted = await self._cleanup_expired_jobs(supabase)

            if requeued > 0 or deleted > 0:
                logger.info(
                    f"Reaper: requeued={requeued}, deleted={deleted}",
                    extra={"requeued": requeued, "deleted": deleted},
                )

        except Exception as e:
            logger.error(f"Reaper cycle failed: {e}")

    async def _requeue_stale_jobs(self, supabase) -> int:
        """Requeue jobs that are stuck in processing state."""
        try:
            # Use the database function
            result = supabase.rpc(
                "requeue_stale_jobs",
                {
                    "lease_seconds": self._lease_seconds,
                    "max_attempts": self._max_attempts,
                },
            ).execute()

            return result.data if result.data else 0

        except Exception as e:
            # Fallback to direct query if function not available
            logger.warning(f"RPC failed, using direct query: {e}")
            return await self._requeue_stale_jobs_direct(supabase)

    async def _requeue_stale_jobs_direct(self, supabase) -> int:
        """Direct SQL fallback for requeuing stale jobs."""
        try:
            from datetime import timedelta

            cutoff = (
                datetime.now(timezone.utc) - timedelta(seconds=self._lease_seconds)
            ).isoformat()

            # Requeue jobs under max attempts
            result = (
                supabase.table("jobs")
                .update(
                    {
                        "status": "queued",
                        "locked_at": None,
                        "locked_by": None,
                    }
                )
                .eq("status", "processing")
                .lt("locked_at", cutoff)
                .lt("attempts", self._max_attempts)
                .execute()
            )

            requeued = len(result.data) if result.data else 0

            # Mark jobs over max attempts as error
            supabase.table("jobs").update(
                {
                    "status": "error",
                    "error": "Max attempts exceeded",
                    "error_code": "MAX_ATTEMPTS",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("status", "processing").lt("locked_at", cutoff).gte(
                "attempts", self._max_attempts
            ).execute()

            return requeued

        except Exception as e:
            logger.error(f"Direct requeue failed: {e}")
            return 0

    async def _cleanup_expired_jobs(self, supabase) -> int:
        """Delete expired completed jobs."""
        try:
            # Use the database function
            result = supabase.rpc("cleanup_expired_jobs").execute()
            return result.data if result.data else 0

        except Exception as e:
            # Fallback to direct query
            logger.warning(f"Cleanup RPC failed, using direct query: {e}")
            return await self._cleanup_expired_jobs_direct(supabase)

    async def _cleanup_expired_jobs_direct(self, supabase) -> int:
        """Direct SQL fallback for cleanup."""
        try:
            now = datetime.now(timezone.utc).isoformat()

            result = (
                supabase.table("jobs")
                .delete()
                .lt("expires_at", now)
                .in_("status", ["done", "error", "cancelled"])
                .execute()
            )

            return len(result.data) if result.data else 0

        except Exception as e:
            logger.error(f"Direct cleanup failed: {e}")
            return 0

    async def reap_now(self) -> dict:
        """Manually trigger a reap cycle. Returns stats."""
        supabase = self._get_supabase()
        if not supabase:
            return {"error": "Supabase not configured"}

        try:
            requeued = await self._requeue_stale_jobs(supabase)
            deleted = await self._cleanup_expired_jobs(supabase)
            return {"requeued": requeued, "deleted": deleted}
        except Exception as e:
            return {"error": str(e)}


# Singleton instance
job_reaper = JobReaper()
