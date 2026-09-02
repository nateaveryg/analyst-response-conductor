variable "project_id" {
  type        = string
  default     = "riccardo-blog-test-v1"
  description = "Google Cloud Project ID where demonstration sandboxes will be provisioned."
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "Google Cloud region for regional testbed resources (Cloud Run, GKE, Artifact Registry)."
}

variable "environment_prefix" {
  type        = string
  default     = "analyst-demo"
  description = "Resource prefix applied to all instantiated demo sandbox components."
}

variable "gke_cluster_name" {
  type        = string
  default     = "cnap-autopilot-mesh"
  description = "Name of the GKE Autopilot multi-cluster service mesh demo target."
}

variable "artifact_repo_name" {
  type        = string
  default     = "secure-slsa-repo"
  description = "Repository name for SLSA Level 3 verified Docker image storage."
}
