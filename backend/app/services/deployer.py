from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)


async def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()


def _generate_dockerfile(deploy_dir: Path) -> None:
    dockerfile = deploy_dir / "Dockerfile"
    dockerfile.write_text(
        "FROM nginx:alpine\n"
        "COPY . /usr/share/nginx/html/\n"
        "EXPOSE 80\n"
    )


async def build_and_push(deployment_id: str, deploy_dir: Path) -> str:
    """Build container image and push to Artifact Registry. Returns image URL."""
    _generate_dockerfile(deploy_dir)

    image_tag = f"{settings.ar_image_base}/{deployment_id}:latest"

    # Use gcloud builds submit
    rc, out, err = await _run([
        "gcloud", "builds", "submit",
        "--tag", image_tag,
        "--project", settings.gcp_project_id,
        "--region", settings.gcp_region,
        "--quiet",
    ], cwd=str(deploy_dir))

    if rc != 0:
        logger.error("Cloud Build failed: %s", err)
        raise RuntimeError(f"Cloud Build failed: {err[-500:]}")

    logger.info("Image built: %s", image_tag)
    return image_tag


async def terraform_apply(
    deployment_id: str,
    image_url: str,
    mode: str,
    security_status: str,
) -> str:
    """Run terraform apply and return the Cloud Run URL."""
    tf_dir = str(settings.terraform_dir)
    workspace = f"airlock-{deployment_id[:12]}"

    # Init with backend config
    rc, out, err = await _run([
        "terraform", "init",
        f"-backend-config=bucket={settings.tf_state_bucket}",
        "-reconfigure",
    ], cwd=tf_dir)
    if rc != 0:
        raise RuntimeError(f"Terraform init failed: {err[-500:]}")

    # Create or select workspace
    rc, _, _ = await _run(["terraform", "workspace", "new", workspace], cwd=tf_dir)
    if rc != 0:
        # Workspace may already exist
        rc, _, err = await _run(["terraform", "workspace", "select", workspace], cwd=tf_dir)
        if rc != 0:
            raise RuntimeError(f"Terraform workspace select failed: {err[-500:]}")

    # Apply
    rc, out, err = await _run([
        "terraform", "apply", "-auto-approve",
        f"-var=project_id={settings.gcp_project_id}",
        f"-var=region={settings.gcp_region}",
        f"-var=deployment_id={deployment_id[:12]}",
        f"-var=image_url={image_url}",
        f"-var=mode={mode}",
        f"-var=security_scan={security_status or 'unknown'}",
    ], cwd=tf_dir)

    if rc != 0:
        logger.error("Terraform apply failed: %s", err)
        raise RuntimeError(f"Terraform apply failed: {err[-500:]}")

    # Get output
    rc, out, err = await _run(
        ["terraform", "output", "-json", "service_url"], cwd=tf_dir
    )
    if rc != 0:
        raise RuntimeError(f"Terraform output failed: {err[-500:]}")

    url = json.loads(out.strip())
    logger.info("Deployed %s to %s", deployment_id, url)
    return url


async def terraform_destroy(deployment_id: str) -> None:
    """Destroy a deployment's infrastructure."""
    tf_dir = str(settings.terraform_dir)
    workspace = f"airlock-{deployment_id[:12]}"

    # Init
    rc, _, err = await _run([
        "terraform", "init",
        f"-backend-config=bucket={settings.tf_state_bucket}",
        "-reconfigure",
    ], cwd=tf_dir)
    if rc != 0:
        logger.error("Terraform init for destroy failed: %s", err)
        return

    # Select workspace
    rc, _, err = await _run(["terraform", "workspace", "select", workspace], cwd=tf_dir)
    if rc != 0:
        logger.warning("Workspace %s not found, may already be destroyed", workspace)
        return

    # Destroy
    rc, out, err = await _run([
        "terraform", "destroy", "-auto-approve",
        f"-var=project_id={settings.gcp_project_id}",
        f"-var=region={settings.gcp_region}",
        f"-var=deployment_id={deployment_id[:12]}",
        f"-var=image_url=placeholder",
        f"-var=mode=demo",
    ], cwd=tf_dir)

    if rc != 0:
        logger.error("Terraform destroy failed: %s", err)
        return

    # Switch to default workspace and delete the old one
    await _run(["terraform", "workspace", "select", "default"], cwd=tf_dir)
    await _run(["terraform", "workspace", "delete", workspace], cwd=tf_dir)
    logger.info("Destroyed workspace %s", workspace)
