
import asyncio
import psutil
from loguru import logger as log

from shared_db_clients.postgres_client import PostgresClient
from shared_db_clients.redis_client import CustomRedisClient

async def health_check(
    postgres_client: PostgresClient,
    redis_client: CustomRedisClient,
):
    """
    Performs a runtime health check.
    """
    # PostgreSQL connections
    pg_stats = {}
    # Accessing protected members (_pool) is risky but acceptable for health checks within the same trust boundary.
    if hasattr(postgres_client, "_pool") and postgres_client._pool and not postgres_client._pool._closed:
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
        # Check backlog for the primary market data stream
        stream_backlog = await pool.xlen("stream:market_data")
    except Exception as e:
        log.warning(f"Could not get stream backlog length: {e}")
        stream_backlog = -1

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