terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required Cloud APIs
resource "google_project_service" "networking_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "iap.googleapis.com",
    "run.googleapis.com",
    "vpcaccess.googleapis.com",
    "certificatemanager.googleapis.com"
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# 2. VPC Network & Serverless Connector
resource "google_compute_network" "conductor_vpc" {
  name                    = "conductor-vpc-${var.environment}"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "conductor_subnet" {
  name          = "conductor-subnet-${var.region}"
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
  network       = google_compute_network.conductor_vpc.id
}

resource "google_vpc_access_connector" "serverless_connector" {
  name          = "conductor-vpc-conn"
  region        = var.region
  network       = google_compute_network.conductor_vpc.name
  ip_cidr_range = "10.8.0.0/28"
  min_instances = 2
  max_instances = 5
}

# 3. Serverless Network Endpoint Group (NEG) for Cloud Run
resource "google_compute_region_network_endpoint_group" "cloudrun_neg" {
  name                  = "conductor-run-neg-${var.environment}"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = var.cloud_run_service_name
  }
}

# 4. Cloud Armor Enterprise Security Policy
resource "google_compute_security_policy" "cloud_armor_policy" {
  name        = "conductor-armor-policy-${var.environment}"
  description = "Cloud Armor enterprise WAF and rate limiting policy for Conductor"

  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule for authenticated enterprise traffic"
  }

  rule {
    action   = "deny(403)"
    priority = "1000"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-v33-stable') || evaluatePreconfiguredExpr('xss-v33-stable')"
      }
    }
    description = "Block OWASP Top 10 SQLi and XSS injection vectors"
  }

  rule {
    action   = "rate_based_ban"
    priority = "2000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 1000
        interval_sec = 60
      }
      ban_duration_sec = 300
    }
    description = "Rate limit abuse protection (1000 req/min/IP)"
  }
}

# 5. Backend Service with IAP / BeyondCorp Authentication
resource "google_compute_backend_service" "conductor_backend" {
  name                  = "conductor-backend-svc-${var.environment}"
  protocol              = "HTTPS"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  security_policy       = google_compute_security_policy.cloud_armor_policy.id

  backend {
    group = google_compute_region_network_endpoint_group.cloudrun_neg.id
  }

  iap {
    enabled = true
  }
}

# 6. IAM Binding for BeyondCorp / Identity-Aware Proxy Access
resource "google_iap_web_backend_service_iam_binding" "iap_corporate_users" {
  project             = var.project_id
  web_backend_service = google_compute_backend_service.conductor_backend.name
  role                = "roles/iap.httpsResourceAccessor"
  members = [
    "domain:${var.allowed_corporate_domain}",
  ]
}

# 7. URL Map & HTTPS Proxy
resource "google_compute_url_map" "conductor_url_map" {
  name            = "conductor-url-map-${var.environment}"
  default_service = google_compute_backend_service.conductor_backend.id
}

resource "google_compute_managed_ssl_certificate" "conductor_cert" {
  name = "conductor-cert-${var.environment}"
  managed {
    domains = ["conductor.corp.${var.allowed_corporate_domain}"]
  }
}

resource "google_compute_target_https_proxy" "conductor_https_proxy" {
  name             = "conductor-https-proxy-${var.environment}"
  url_map          = google_compute_url_map.conductor_url_map.id
  ssl_certificates = [google_compute_managed_ssl_certificate.conductor_cert.id]
}

resource "google_compute_global_forwarding_rule" "conductor_forwarding_rule" {
  name                  = "conductor-https-fwd-rule-${var.environment}"
  target                = google_compute_target_https_proxy.conductor_https_proxy.id
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
}
