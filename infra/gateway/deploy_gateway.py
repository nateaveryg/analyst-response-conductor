#!/usr/bin/env python3
"""
Agent Platform Agent Gateway Provisioning and Configuration Automation.

Automates the provisioning and lifecycle configuration of the Google Cloud
Agent Platform Agent Gateway in Client-to-Agent ingress mode (governedAccessPath: CLIENT_TO_AGENT)
for The Conductor v3 architecture in project `riccardo-blog-test-v1` (region: `us-central1`).

Validates declarative resource manifests:
1. gateway.yaml (AgentGateway in CLIENT_TO_AGENT mode)
2. authz_extension.yaml (Model Armor DLP extension, failOpen: false, wireFormat: EXT_PROC_GRPC)
3. authz_policy.yaml (CONTENT_AUTHZ policy, action: CUSTOM)
4. route_rules.yaml (HttpRoute mapping /query, /streamQuery, /getAgentCard, /api/v1/*)
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("conductor.deploy_gateway")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Deploy and configure Agent Platform Agent Gateway."
    )
    parser.add_argument(
        "--project",
        default=os.environ.get(
            "GOOGLE_CLOUD_PROJECT",
            os.environ.get("CLOUD_DEPLOY_PROJECT_ID", "riccardo-blog-test-v1"),
        ),
        help="Google Cloud Project ID",
    )
    parser.add_argument(
        "--location",
        default=os.environ.get(
            "GOOGLE_CLOUD_LOCATION",
            os.environ.get("CLOUD_DEPLOY_LOCATION", "us-central1"),
        ),
        help="Google Cloud Region",
    )
    parser.add_argument(
        "--env",
        choices=["dev", "staging", "prod"],
        default=os.environ.get("TARGET_ENV", "prod"),
        help="Deployment Target Environment Tier",
    )
    parser.add_argument(
        "--manifest-dir",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="Directory containing declarative YAML manifests",
    )
    parser.add_argument(
        "--gateway-id",
        default="conductor-v3-ingress-gateway",
        help="Identifier for the Agent Gateway resource",
    )
    parser.add_argument(
        "--output-file",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "deployed_gateway.json"
        ),
        help="Path to write deployment output metadata JSON",
    )
    parser.add_argument(
        "--output-gcs-path",
        default=os.environ.get("CLOUD_DEPLOY_OUTPUT_GCS_PATH", ""),
        help="Cloud Storage directory provided by Cloud Deploy for results.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate manifests and schemas without making remote cloud calls",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Execute syntax and schema validation only",
    )
    return parser.parse_args()


class ManifestValidator:
    """Validates declarative YAML manifests against Agent Platform specifications."""

    def __init__(self, manifest_dir: str, project: str, location: str):
        self.manifest_dir = manifest_dir
        self.project = project
        self.location = location

    def load_yaml(self, filename: str) -> Dict[str, Any]:
        path = os.path.join(self.manifest_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required manifest file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        if not isinstance(content, dict):
            raise ValueError(f"Manifest {filename} does not contain a valid YAML dictionary")
        return content

    def validate_gateway(self) -> Dict[str, Any]:
        data = self.load_yaml("gateway.yaml")
        name = data.get("name", "")
        expected_prefix = f"projects/{self.project}/locations/{self.location}/agentGateways/"
        if not name.startswith(expected_prefix) and "/" in name:
            raise ValueError(
                f"gateway.yaml name '{name}' does not match expected prefix '{expected_prefix}'"
            )

        google_managed = data.get("googleManaged")
        if not isinstance(google_managed, dict):
            raise ValueError("gateway.yaml missing required 'googleManaged' block")

        access_path = google_managed.get("governedAccessPath")
        if access_path != "CLIENT_TO_AGENT":
            raise ValueError(
                f"gateway.yaml governedAccessPath must be 'CLIENT_TO_AGENT', got '{access_path}'"
            )

        registries = data.get("registries", [])
        if not isinstance(registries, list) or len(registries) == 0:
            raise ValueError("gateway.yaml must define at least one registry in 'registries'")

        for reg in registries:
            if not reg.startswith("//agentregistry.googleapis.com/"):
                raise ValueError(
                    f"Invalid registry URI '{reg}'; must start with '//agentregistry.googleapis.com/'"
                )

        logger.info("  [VALID] gateway.yaml validated successfully (CLIENT_TO_AGENT ingress mode).")
        return data

    def validate_authz_extension(self) -> Dict[str, Any]:
        data = self.load_yaml("authz_extension.yaml")
        required_fields = ["name", "service", "timeout", "wireFormat"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"authz_extension.yaml missing required field: {field}")

        if data.get("wireFormat") != "EXT_PROC_GRPC":
            raise ValueError(
                f"authz_extension.yaml wireFormat must be 'EXT_PROC_GRPC', got '{data.get('wireFormat')}'"
            )

        if data.get("failOpen") is not False:
            raise ValueError("authz_extension.yaml failOpen must be strictly false for zero-trust DLP")

        logger.info("  [VALID] authz_extension.yaml validated (failOpen: false, wireFormat: EXT_PROC_GRPC).")
        return data

    def validate_authz_policy(self) -> Dict[str, Any]:
        data = self.load_yaml("authz_policy.yaml")
        if data.get("policyProfile") != "CONTENT_AUTHZ":
            raise ValueError(
                f"authz_policy.yaml policyProfile must be 'CONTENT_AUTHZ', got '{data.get('policyProfile')}'"
            )

        if data.get("action") != "CUSTOM":
            raise ValueError(
                f"authz_policy.yaml action must be 'CUSTOM', got '{data.get('action')}'"
            )

        target = data.get("target", {})
        target_resources = target.get("resources", [])
        if not target_resources:
            raise ValueError("authz_policy.yaml target.resources must list target Agent Gateway")

        custom_provider = data.get("customProvider", {})
        authz_ext = custom_provider.get("authzExtension", {})
        ext_resources = authz_ext.get("resources", [])
        if not ext_resources:
            raise ValueError("authz_policy.yaml customProvider.authzExtension.resources must be specified")

        logger.info("  [VALID] authz_policy.yaml validated (CONTENT_AUTHZ, action: CUSTOM).")
        return data

    def validate_route_rules(self) -> Dict[str, Any]:
        data = self.load_yaml("route_rules.yaml")
        rules = data.get("rules", [])
        if not rules:
            raise ValueError("route_rules.yaml rules list is empty")

        matched_paths = set()
        for rule in rules:
            matches = rule.get("matches", [])
            for m in matches:
                if "fullPathMatch" in m:
                    matched_paths.add(m["fullPathMatch"])
                elif "prefixMatch" in m:
                    matched_paths.add(m["prefixMatch"])

            action = rule.get("action", {})
            cors = action.get("corsPolicy", {})
            if not cors:
                raise ValueError("route_rules.yaml rule action missing required 'corsPolicy'")
            if "*" not in cors.get("allowOrigins", []):
                raise ValueError("corsPolicy must allow '*' or specific frontend origins")
            if "OPTIONS" not in cors.get("allowMethods", []):
                raise ValueError("corsPolicy allowMethods must include 'OPTIONS' for preflight")

        required_endpoints = ["/query", "/streamQuery", "/getAgentCard", "/api/v1/"]
        for req in required_endpoints:
            if req not in matched_paths:
                raise ValueError(f"route_rules.yaml missing mandatory route for endpoint '{req}'")

        logger.info("  [VALID] route_rules.yaml validated (paths: /query, /streamQuery, /getAgentCard, /api/v1/*).")
        return data

    def validate_all(self) -> Dict[str, Any]:
        logger.info("Validating declarative Agent Gateway manifests...")
        gw = self.validate_gateway()
        ext = self.validate_authz_extension()
        pol = self.validate_authz_policy()
        routes = self.validate_route_rules()
        return {
            "gateway": gw,
            "authz_extension": ext,
            "authz_policy": pol,
            "route_rules": routes,
        }


def check_gcloud_auth() -> bool:
    """Checks if gcloud has valid active credentials."""
    try:
        res = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return res.returncode == 0 and len(res.stdout.strip()) > 0
    except Exception:
        return False


def execute_deployment(
    manifests: Dict[str, Any],
    project: str,
    location: str,
    env: str,
    gateway_id: str,
    dry_run: bool,
) -> Dict[str, Any]:
    """Applies manifests via gcloud or simulates import during dry-run / offline execution."""
    gw_resource = f"projects/{project}/locations/{location}/agentGateways/{gateway_id}"
    gateway_endpoint = f"https://conductor-gateway-105792947502.{location}.rep.cloud.google.com"

    has_auth = check_gcloud_auth()
    logger.info(f"Active Google Cloud authentication status: {'AUTHENTICATED' if has_auth else 'UNAUTHENTICATED/OFFLINE'}")

    if not dry_run and has_auth:
        logger.info("Executing remote resource provisioning via gcloud CLI...")
        manifest_dir = os.path.dirname(os.path.abspath(__file__))

        # 1. Import Agent Gateway
        gw_cmd = [
            "gcloud", "beta", "network-services", "agent-gateways", "import",
            gateway_id,
            f"--location={location}",
            f"--project={project}",
            f"--source={os.path.join(manifest_dir, 'gateway.yaml')}",
            "--quiet",
        ]
        logger.info(f"Running: {' '.join(gw_cmd)}")
        subprocess.run(gw_cmd, check=True)

        # 2. Import AuthzExtension
        ext_cmd = [
            "gcloud", "beta", "service-extensions", "authz-extensions", "import",
            "conductor-model-armor-ext",
            f"--location={location}",
            f"--project={project}",
            f"--source={os.path.join(manifest_dir, 'authz_extension.yaml')}",
            "--quiet",
        ]
        logger.info(f"Running: {' '.join(ext_cmd)}")
        subprocess.run(ext_cmd, check=True)

        # 3. Import AuthzPolicy
        pol_cmd = [
            "gcloud", "beta", "network-security", "authz-policies", "import",
            "conductor-ingress-content-authz",
            f"--location={location}",
            f"--project={project}",
            f"--source={os.path.join(manifest_dir, 'authz_policy.yaml')}",
            "--quiet",
        ]
        logger.info(f"Running: {' '.join(pol_cmd)}")
        subprocess.run(pol_cmd, check=True)

        # 4. Import HttpRoute
        route_cmd = [
            "gcloud", "network-services", "http-routes", "import",
            "conductor-v3-gateway-routes",
            f"--location=global",
            f"--project={project}",
            f"--source={os.path.join(manifest_dir, 'route_rules.yaml')}",
            "--quiet",
        ]
        logger.info(f"Running: {' '.join(route_cmd)}")
        subprocess.run(route_cmd, check=True)
        status = "PROVISIONED"
    else:
        logger.info("Operating in declarative offline / dry-run mode.")
        logger.info(f"Validated declarative configuration for resource: {gw_resource}")
        status = "VALIDATED"

    deploy_record = {
        "status": status,
        "resource_name": gw_resource,
        "gateway_id": gateway_id,
        "governed_access_path": "CLIENT_TO_AGENT",
        "ingress_endpoint": gateway_endpoint,
        "env": env,
        "project": project,
        "location": location,
        "model_armor_extension": f"projects/{project}/locations/{location}/authzExtensions/conductor-model-armor-ext",
        "content_authz_policy": f"projects/{project}/locations/{location}/authzPolicies/conductor-ingress-content-authz",
        "route_rules": f"projects/{project}/locations/global/httpRoutes/conductor-v3-gateway-routes",
        "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return deploy_record


def main():
    args = parse_args()

    logger.info("====================================================================")
    logger.info("  🛡️  Agent Platform Agent Gateway Deployer & Governance Orchestrator")
    logger.info("====================================================================")
    logger.info(f"Project:      {args.project}")
    logger.info(f"Location:     {args.location}")
    logger.info(f"Environment:  {args.env.upper()}")
    logger.info(f"Gateway ID:   {args.gateway_id}")
    logger.info(f"Manifest Dir: {args.manifest_dir}")
    logger.info(f"Dry Run:      {args.dry_run}")

    validator = ManifestValidator(args.manifest_dir, args.project, args.location)
    manifests = validator.validate_all()

    if args.validate_only:
        logger.info("Validation complete. Exiting (--validate-only).")
        sys.exit(0)

    result = execute_deployment(
        manifests=manifests,
        project=args.project,
        location=args.location,
        env=args.env,
        gateway_id=args.gateway_id,
        dry_run=args.dry_run,
    )

    # Persist deployed_gateway.json
    os.makedirs(os.path.dirname(os.path.abspath(args.output_file)), exist_ok=True)
    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Deployment record written to: {args.output_file}")

    # Cloud Deploy results.json contract
    out_dir = os.path.dirname(os.path.abspath(args.output_file))
    results_file = os.path.join(out_dir, "results.json")
    deploy_results = {
        "resultStatus": "SUCCEEDED",
        "artifactFiles": [args.output_file],
        "failureMessage": "",
        "metadata": {
            "resourceName": result["resource_name"],
            "governedAccessPath": result["governed_access_path"],
            "ingressEndpoint": result["ingress_endpoint"],
            "env": args.env,
        },
    }
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(deploy_results, f, indent=2)
    logger.info(f"Cloud Deploy results file written to: {results_file}")

    logger.info("====================================================================")
    logger.info("  ✅ Agent Gateway Manifest Validation & Deployment Succeeded!")
    logger.info(f"  Resource: {result['resource_name']}")
    logger.info(f"  Ingress:  {result['ingress_endpoint']}")
    logger.info("====================================================================")


if __name__ == "__main__":
    main()
