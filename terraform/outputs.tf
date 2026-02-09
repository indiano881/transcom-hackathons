output "service_url" {
  description = "The Cloud Run service URL"
  value       = module.deployment.service_url
}

output "service_name" {
  description = "The Cloud Run service name"
  value       = module.deployment.service_name
}
