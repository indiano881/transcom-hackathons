output "service_url" {
  description = "The Cloud Run service URL"
  value       = google_cloud_run_v2_service.deployment.uri
}

output "service_name" {
  description = "The Cloud Run service name"
  value       = google_cloud_run_v2_service.deployment.name
}
