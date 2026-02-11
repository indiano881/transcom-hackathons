import subprocess
from pathlib import Path
from pydantic_settings import BaseSettings


def _detect_gcp_project() -> str:
    try:
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True, text=True, timeout=10
        )
        project = result.stdout.strip()
        if project and project != "(unset)":
            return project
    except Exception:
        pass
    return ""


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    gcp_project_id: str = ""
    gcp_region: str = "europe-north1"
    ar_repo_name: str = "airlock-images"
    tf_state_bucket: str = ""
    base_dir: Path = Path(__file__).resolve().parent.parent
    deployments_dir: Path = Path(__file__).resolve().parent.parent / "deployments"
    plugin_working_directory: Path = Path(__file__).resolve().parent.parent / "plugin-working-directory"
    terraform_dir: Path = Path(__file__).resolve().parent.parent.parent / "terraform"
    db_path: Path = Path(__file__).resolve().parent.parent / "airlock.db"
    demo_ttl_seconds: int = 3600  # 1 hour
    cleanup_interval_seconds: int = 60

    jwt_secret_key: str = "0e23078e3ad17442ff9fecbf20f41a4f"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    enable_deploy: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def resolve_gcp(self) -> None:
        if not self.gcp_project_id:
            self.gcp_project_id = _detect_gcp_project()
        if not self.tf_state_bucket and self.gcp_project_id:
            self.tf_state_bucket = f"{self.gcp_project_id}-airlock-tf-state"

    @property
    def ar_image_base(self) -> str:
        return f"{self.gcp_region}-docker.pkg.dev/{self.gcp_project_id}/{self.ar_repo_name}"


settings = Settings()
settings.resolve_gcp()
