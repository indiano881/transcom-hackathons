module "deployment" {
  source = "./modules/airlock-deployment"

  project_id    = var.project_id
  region        = var.region
  deployment_id = var.deployment_id
  image_url     = var.image_url
  mode          = var.mode
  creator       = var.creator
  security_scan = var.security_scan
}
