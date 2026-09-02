# ==============================================================================
# Analyst Response Agent (ARA) — Phase 5: On-Demand Demo Sandbox Infrastructure
# Target Project: riccardo-blog-test-v1 (us-central1)
# Provisions 5 isolated demonstration testbeds for Gartner MQ, Forrester Wave,
# and IDC MarketScape evaluation recordings and storyboard verification.
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.20.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ------------------------------------------------------------------------------
# 0. Core GCP Service Enablement
# ------------------------------------------------------------------------------
resource "google_project_service" "enabled_apis" {
  for_each = toset([
    "run.googleapis.com",
    "container.googleapis.com",
    "artifactregistry.googleapis.com",
    "binaryauthorization.googleapis.com",
    "monitoring.googleapis.com",
    "iam.googleapis.com",
    "aiplatform.googleapis.com"
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# ------------------------------------------------------------------------------
# 1. Module 1 Testbed: Serverless Concurrency & AI Agent Service (Cloud Run)
# ------------------------------------------------------------------------------
resource "google_cloud_run_v2_service" "conductor_demo_service" {
  name     = "${var.environment_prefix}-conductor-concurrency-demo"
  location = var.region
  project  = var.project_id

  template {
    scaling {
      max_instance_count = 10
      min_instance_count = 1
    }
    max_instance_request_concurrency = 80

    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello:latest"
      resources {
        limits = {
          cpu    = "2"
          memory = "2048Mi"
        }
      }
      env {
        name  = "VERTEX_AI_MODEL"
        value = "gemini-3.5-flash"
      }
    }
  }

  depends_on = [google_project_service.enabled_apis]
}

# ------------------------------------------------------------------------------
# 2. Module 2 Testbed: GKE Autopilot Multi-Cluster Mesh (Kubernetes Engine)
# ------------------------------------------------------------------------------
resource "google_container_cluster" "autopilot_mesh_demo" {
  name             = "${var.environment_prefix}-${var.gke_cluster_name}"
  location         = var.region
  project          = var.project_id
  enable_autopilot = true

  network_policy {
    enabled = true
  }

  release_channel {
    channel = "REGULAR"
  }

  ip_allocation_policy {
    cluster_ipv4_cidr_block  = "/16"
    services_ipv4_cidr_block = "/22"
  }

  depends_on = [google_project_service.enabled_apis]
}

# ------------------------------------------------------------------------------
# 3. Module 3 Testbed: SLSA Level 3 Software Supply Chain (Artifact Registry)
# ------------------------------------------------------------------------------
resource "google_artifact_registry_repository" "slsa_repo" {
  location      = var.region
  repository_id = "${var.environment_prefix}-${var.artifact_repo_name}"
  description   = "Verified container repository supporting SLSA Level 3 provenence build attestation and Binary Authorization"
  format        = "DOCKER"
  project       = var.project_id

  docker_config {
    immutable_tags = true
  }

  depends_on = [google_project_service.enabled_apis]
}

# ------------------------------------------------------------------------------
# 4. Module 4 & 5 Testbeds: Enterprise Governance & Workload Identity Federation
# ------------------------------------------------------------------------------
resource "google_iam_workload_identity_pool" "enterprise_pool" {
  project                   = var.project_id
  workload_identity_pool_id = "${var.environment_prefix}-pool-demo"
  display_name              = "Analyst Evaluation Workload Identity Pool"
  description               = "Federated OIDC pool for GitHub Actions & GitLab CI/CD secure deployments without long-lived keys"
  disabled                  = false

  depends_on = [google_project_service.enabled_apis]
}
