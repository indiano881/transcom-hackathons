variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "deployment_id" {
  description = "Unique deployment identifier"
  type        = string
}

variable "image_url" {
  description = "Full Artifact Registry image URL"
  type        = string
}

variable "mode" {
  description = "Deployment mode: demo or prod"
  type        = string
}

variable "creator" {
  description = "Who created this deployment"
  type        = string
}

variable "security_scan" {
  description = "Security scan result"
  type        = string
}
