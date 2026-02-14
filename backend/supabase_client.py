"""
Supabase client singleton with connection management.

Uses service role key for backend operations (bypasses RLS).
"""

import os
from typing import Optional

from supabase import create_client, Client

from logger_config import setup_logging

logger = setup_logging()

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client singleton.

    Uses SUPABASE_SERVICE_KEY for backend operations (bypasses RLS).

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_SERVICE_KEY not set
    """
    global _supabase_client

    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")

        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set. "
                "Get these from your Supabase project settings."
            )

        _supabase_client = create_client(url, key)
        logger.info("Supabase client initialized")

    return _supabase_client


def is_supabase_configured() -> bool:
    """Check if Supabase environment variables are configured."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    return bool(url and key)


async def close_supabase_client():
    """Close Supabase client on shutdown."""
    global _supabase_client
    if _supabase_client:
        logger.info("Closing Supabase client")
        _supabase_client = None
