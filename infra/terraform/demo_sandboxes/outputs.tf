output "cloud_run_service_url" {
  description = "Deployed Cloud Run service URI for serverless concurrency and AI inferencing testbeds."
  value       = google_cloud_run_v2_service.conductor_demo_service.uri
}

output "gke_cluster_endpoint" {
  description = "GKE Autopilot cluster API server endpoint for multi-cluster mesh demonstrations."
  value       = google_container_cluster.autopilot_mesh_demo.endpoint
}

output "artifact_registry_repository_uri" {
  description = "Docker repository URI for verifying immutable SLSA Level 3 provenence tags."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.slsa_repo.repository_id}"
}

output "workload_identity_pool_name" {
  description = "Resource name of the enterprise federated OIDC Workload Identity pool."
  value       = google_iam_workload_identity_pool.enterprise_pool.name
}

output "console_verification_urls" {
  description = "Direct map of Google Cloud Console verification URLs matching AI Demo Script Architect references."
  value = {
    cloud_run         = "https://console.cloud.google.com/run?project=${var.project_id}"
    kubernetes        = "https://console.cloud.google.com/kubernetes?project=${var.project_id}"
    artifact_registry = "https://console.cloud.google.com/artifacts?project=${var.project_id}"
    monitoring_scc    = "https://console.cloud.google.com/monitoring?project=${var.project_id}"
    iam_admin         = "https://console.cloud.google.com/iam-admin?project=${var.project_id}"
  }
}
