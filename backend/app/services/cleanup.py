import asyncio
import logging
import shutil
from datetime import datetime, timezone

from ..config import settings
from ..database import fetch_all, execute
from .deployer import terraform_destroy

logger = logging.getLogger(__name__)


async def cleanup_expired():
    """Find and destroy expired demo deployments."""
    now = datetime.now(timezone.utc).isoformat()
    rows = await fetch_all(
        "SELECT id FROM deployments WHERE expires_at IS NOT NULL AND expires_at < ? AND status = 'deployed'",
        (now,),
    )

    for row in rows:
        deployment_id = row["id"]
        logger.info("Cleaning up expired deployment: %s", deployment_id)
        try:
            await terraform_destroy(deployment_id)
        except Exception:
            logger.exception("Failed to destroy %s", deployment_id)

        # Remove files
        deploy_dir = settings.deployments_dir / deployment_id
        if deploy_dir.exists():
            shutil.rmtree(deploy_dir, ignore_errors=True)

        # Update DB
        await execute(
            "UPDATE deployments SET status = 'expired' WHERE id = ?",
            (deployment_id,),
        )
        logger.info("Deployment %s marked as expired", deployment_id)


async def cleanup_loop():
    """Background loop that checks for expired deployments."""
    while True:
        try:
            await cleanup_expired()
        except Exception:
            logger.exception("Cleanup loop error")
        await asyncio.sleep(settings.cleanup_interval_seconds)
