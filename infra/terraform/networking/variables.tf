variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
  default     = "riccardo-blog-test-v1"
}

variable "region" {
  type        = string
  description = "Google Cloud Region for networking resources"
  default     = "us-central1"
}

variable "cloud_run_service_name" {
  type        = string
  description = "Target Cloud Run service name"
  default     = "conductor-v2"
}

variable "environment" {
  type        = string
  description = "Environment tier (dev, staging, production)"
  default     = "production"
}

variable "support_email" {
  type        = string
  description = "OAuth brand support email"
  default     = "averyn@google.com"
}

variable "allowed_corporate_domain" {
  type        = string
  description = "Allowed corporate domain for IAP access"
  default     = "google.com"
}
