output "load_balancer_ip" {
  description = "Global IP address of the managed Application Load Balancer"
  value       = google_compute_global_forwarding_rule.conductor_forwarding_rule.ip_address
}

output "corporate_url" {
  description = "Enterprise corporate intranet URL protected by BeyondCorp / IAP"
  value       = "https://conductor.corp.${var.allowed_corporate_domain}"
}

output "serverless_connector_id" {
  description = "VPC Serverless Connector ID for Cloud Run private routing"
  value       = google_vpc_access_connector.serverless_connector.id
}

output "cloud_armor_policy_name" {
  description = "Name of the active Cloud Armor security policy"
  value       = google_compute_security_policy.cloud_armor_policy.name
}

output "iap_backend_service_name" {
  description = "Backend service name with IAP enabled"
  value       = google_compute_backend_service.conductor_backend.name
}
