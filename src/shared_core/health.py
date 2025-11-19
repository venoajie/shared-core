# core/health.py
import asyncio
import psutil
from loguru import logger as log

from core.db.postgres import PostgresClient
from core.db.redis import CustomRedisClient

# --- Configuration for the new time sanity check ---
TIME_SOURCES = [
    "http://worldtimeapi.org/api/timezone/Etc/UTC",
    "https://www.google.com",
    "https://www.cloudflare.com/cdn-cgi/trace",  # This is a text-based endpoint
]
# The maximum acceptable difference between system time and real time (in seconds).
MAX_TIME_SKEW_SECONDS = 60


async def health_check(
    postgres_client: PostgresClient,
    redis_client: CustomRedisClient,
):
    """
    Performs a runtime health check, gathering statistics on connections,
    memory usage, and stream backlogs.
    """
    # PostgreSQL connections
    pg_stats = {}
    if postgres_client._pool and not postgres_client._pool._closed:
        try:
            pg_stats = {
                "connections": postgres_client._pool.get_size(),
                "idle": postgres_client._pool.get_idle_size(),
            }
        except Exception as e:
            log.warning(f"Could not get PostgreSQL pool stats: {e}")
            pg_stats = {"error": str(e)}

    # Redis connections
    redis_stats = {}
    try:
        pool = await redis_client.get_pool()
        # This is an approximation; aioredis doesn't expose a simple connection count.
        # We can check the number of connections in the pool's internal list.
        redis_stats = {
            "pool_connections": len(pool.connection_pool._available_connections)
        }
    except Exception as e:
        log.warning(f"Could not get Redis pool stats: {e}")
        redis_stats = {"error": str(e)}

    # Memory diagnostics
    process = psutil.Process()
    mem_info = process.memory_full_info()

    # Stream backlog monitoring
    stream_backlog = 0
    try:
        pool = await redis_client.get_pool()
        stream_backlog = await pool.xlen("stream:market_data")
    except Exception as e:
        log.warning(f"Could not get stream backlog length: {e}")
        stream_backlog = -1  # Indicate an error

    return {
        "postgres": pg_stats,
        "redis": redis_stats,
        "memory": {
            "rss_mb": round(mem_info.rss / 1024 / 1024, 2),
            "uss_mb": round(mem_info.uss / 1024 / 1024, 2),
            "swap_mb": round(mem_info.swap / 1024 / 1024, 2),
        },
        "stream_backlog": stream_backlog,
        "process": {
            "open_files": len(process.open_files()),
            "threads": process.num_threads(),
        },
    }
