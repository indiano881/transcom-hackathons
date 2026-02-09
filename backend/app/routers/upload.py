import json
import uuid
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from ..config import settings
from ..database import execute
from ..models import UploadResponse
from ..services.zip_handler import validate_and_extract, ZipValidationError
from ..services.ai_analyzer import run_all_checks

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_zip(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")

    deployment_id = uuid.uuid4().hex[:16]
    deploy_dir = settings.deployments_dir / deployment_id
    name = Path(file.filename).stem

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        # Validate and extract
        meta = validate_and_extract(tmp_path, deploy_dir)
    except ZipValidationError as e:
        # Clean up on error
        if deploy_dir.exists():
            shutil.rmtree(deploy_dir)
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)

    # Run AI checks concurrently
    checks = await run_all_checks(deploy_dir)

    now = datetime.now(timezone.utc).isoformat()

    # Store in DB
    await execute(
        """INSERT INTO deployments
           (id, name, status, file_count, total_size,
            security_status, security_details,
            cost_status, cost_details,
            brand_status, brand_details,
            created_at)
           VALUES (?, ?, 'checked', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            deployment_id,
            name,
            meta["file_count"],
            meta["total_size"],
            checks["security"].status,
            json.dumps({"summary": checks["security"].summary, "details": checks["security"].details}),
            checks["cost"].status,
            json.dumps({"summary": checks["cost"].summary, "details": checks["cost"].details}),
            checks["brand"].status,
            json.dumps({"summary": checks["brand"].summary, "details": checks["brand"].details}),
            now,
        ),
    )

    return UploadResponse(
        deployment_id=deployment_id,
        name=name,
        file_count=meta["file_count"],
        total_size=meta["total_size"],
        security=checks["security"],
        cost=checks["cost"],
        brand=checks["brand"],
    )
