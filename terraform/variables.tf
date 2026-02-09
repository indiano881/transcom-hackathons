variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-north1"
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
  default     = "demo"

  validation {
    condition     = contains(["demo", "prod"], var.mode)
    error_message = "Mode must be 'demo' or 'prod'."
  }
}

variable "creator" {
  description = "Who created this deployment"
  type        = string
  default     = "airlock-user"
}

variable "security_scan" {
  description = "Security scan result: pass, warn, or fail"
  type        = string
  default     = "unknown"
}
