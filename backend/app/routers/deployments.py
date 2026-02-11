import logging
import json
import shutil
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..database import execute, fetch_one, fetch_all
from ..models import Deployment, DeployRequest, DeployResponse
from ..services.deployer import build_and_push, terraform_apply, terraform_destroy

logger = logging.getLogger(__name__)
router = APIRouter()


def _row_to_deployment(row) -> Deployment:
    return Deployment(**dict(row))


@router.get("/deployments", response_model=list[Deployment])
async def list_deployments():
    rows = await fetch_all(
        "SELECT * FROM deployments ORDER BY created_at DESC"
    )
    return [_row_to_deployment(r) for r in rows]


@router.get("/deployments/{deployment_id}", response_model=Deployment)
async def get_deployment(deployment_id: str):
    row = await fetch_one("SELECT * FROM deployments WHERE id = ?", (deployment_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return _row_to_deployment(row)


@router.post("/deployments/{deployment_id}/deploy", response_model=DeployResponse)
async def deploy(deployment_id: str, req: DeployRequest):
    logger.info('deployment_id = %s', deployment_id)
    row = await fetch_one("SELECT * FROM deployments WHERE id = ?", (deployment_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if row["status"] not in ("checked", "deployed"):
        raise HTTPException(status_code=400, detail=f"Cannot deploy: status is '{row['status']}'")

    # Block deployment if security check failed
    if row["security_status"] == "fail":
        raise HTTPException(
            status_code=403,
            detail="Deployment blocked: security scan failed. Fix security issues and re-upload."
        )

    if req.mode not in ("demo", "prod"):
        raise HTTPException(status_code=400, detail="Mode must be 'demo' or 'prod'")

    deploy_dir = settings.deployments_dir / deployment_id
    logger.info('deploy_dir = %s', deploy_dir)
    if not deploy_dir.exists():
        raise HTTPException(status_code=404, detail="Deployment files not found")

    # Update status to deploying
    await execute(
        "UPDATE deployments SET status = 'deploying', mode = ? WHERE id = ?",
        (req.mode, deployment_id),
    )

    try:
        if settings.enable_deploy:
            # Build and push image
            image_url = await build_and_push(deployment_id, deploy_dir)

            # Terraform apply
            cloud_run_url = await terraform_apply(
                deployment_id=deployment_id,
                image_url=image_url,
                mode=req.mode,
                security_status=row["security_status"] or "unknown",
            )
        else:
            logger.warning(f"settings.enable_deploy is {settings.enable_deploy}, shouldn't deploy it")
            cloud_run_url = 'fake url'
    except Exception as e:
        await execute(
            "UPDATE deployments SET status = 'failed' WHERE id = ?",
            (deployment_id,),
        )
        raise HTTPException(status_code=500, detail=str(e))

    now = datetime.now(timezone.utc)
    expires_at = None
    if req.mode == "demo":
        expires_at = (now + timedelta(seconds=settings.demo_ttl_seconds)).isoformat()

    await execute(
        """UPDATE deployments
           SET status = 'deployed', cloud_run_url = ?, deployed_at = ?, expires_at = ?
           WHERE id = ?""",
        (cloud_run_url, now.isoformat(), expires_at, deployment_id),
    )

    return DeployResponse(
        deployment_id=deployment_id,
        cloud_run_url=cloud_run_url,
        mode=req.mode,
        expires_at=expires_at,
    )


@router.delete("/deployments/{deployment_id}")
async def delete_deployment(deployment_id: str):
    row = await fetch_one("SELECT * FROM deployments WHERE id = ?", (deployment_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Deployment not found")

    # Terraform destroy if deployed
    if row["status"] == "deployed" and row["cloud_run_url"]:
        try:
            await terraform_destroy(deployment_id)
        except Exception:
            pass  # Best effort

    # Remove files
    deploy_dir = settings.deployments_dir / deployment_id
    if deploy_dir.exists():
        shutil.rmtree(deploy_dir, ignore_errors=True)

    await execute("DELETE FROM deployments WHERE id = ?", (deployment_id,))
    return {"status": "deleted", "deployment_id": deployment_id}
