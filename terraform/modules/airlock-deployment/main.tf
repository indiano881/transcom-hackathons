resource "google_cloud_run_v2_service" "deployment" {
  name     = "airlock-${var.deployment_id}"
  location = var.region
  project  = var.project_id

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = var.image_url

      ports {
        container_port = 80
      }

      resources {
        limits = {
          memory = "512Mi"
        }
      }
    }
  }

  labels = {
    "managed-by"    = "airlock"
    "creator"       = var.creator
    "mode"          = var.mode
    "security-scan" = var.security_scan
  }
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.deployment.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
