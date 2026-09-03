"""
Unit and Integration Tests for Conductor v3 Containerization and Dev2Prod Pipeline.
Validates:
1. Multi-stage distroless Dockerfile (Dockerfile.v3) architecture.
2. Cloud Build CI pipeline configuration (cloudbuild-v3.yaml).
3. Cloud Deploy CD pipeline and Canary release configuration (clouddeploy-v3.yaml).
4. Skaffold rendering configuration (skaffold-v3.yaml).
5. Knative / Cloud Run production service manifest (infra/cloudrun/service-v3.yaml).
"""
import os
import unittest
import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def load_yaml_documents(filepath):
    """Loads all YAML documents from a file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return list(yaml.safe_load_all(f))


class TestConductorV3ContainerAndPipeline(unittest.TestCase):
    """Verifies Conductor v3 Docker packaging and Cloud Deploy release manifests."""

    def test_01_dockerfile_v3_multistage_distroless_architecture(self):
        """Verifies Dockerfile.v3 multi-stage distroless build specification."""
        dockerfile_path = os.path.join(REPO_ROOT, "Dockerfile.v3")
        self.assertTrue(os.path.exists(dockerfile_path), "Dockerfile.v3 must exist")

        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Stage 2: Go Builder
        self.assertIn("FROM golang:", content)
        self.assertTrue(
            "AS go-builder" in content or "AS builder" in content,
            "Dockerfile.v3 must define a Go builder stage",
        )
        self.assertIn("CGO_ENABLED=0", content)
        self.assertIn("GOOS=linux", content)
        self.assertIn("-ldflags=\"-s -w -extldflags '-static'\"", content)

        # Stage 3: Distroless Non-Root Runtime
        self.assertIn("FROM gcr.io/distroless/static-debian12:nonroot", content)
        self.assertIn("USER nonroot:nonroot", content)
        self.assertTrue(
            "COPY --from=go-builder /app/conductor-server /conductor-server" in content
            or "COPY --from=builder /app/conductor-server /conductor-server" in content,
            "Dockerfile.v3 must copy compiled Go binary to /conductor-server",
        )
        self.assertTrue(
            'ENTRYPOINT ["/app/conductor-server"]' in content
            or 'ENTRYPOINT ["/conductor-server"]' in content,
            "Dockerfile.v3 must define the binary entrypoint",
        )
        self.assertIn("EXPOSE 8080", content)
        self.assertIn("ENV SERVICE_VERSION=3.3.2", content)
        self.assertIn("ENV VERIFICATION_MARKER=v3.3.2-verified", content)

        # Frontend Dockerfile verification
        fe_dockerfile = os.path.join(REPO_ROOT, "Dockerfile.frontend")
        self.assertTrue(os.path.exists(fe_dockerfile), "Dockerfile.frontend must exist")
        with open(fe_dockerfile, "r", encoding="utf-8") as f:
            fe_content = f.read()
        self.assertIn("ENV SERVICE_VERSION=3.3.1", fe_content)
        self.assertIn("ENV VERIFICATION_MARKER=v3.3.1-verified", fe_content)

        # Backend Dockerfile verification (Agent Engine pipeline)
        be_dockerfile = os.path.join(REPO_ROOT, "backend", "Dockerfile")
        self.assertTrue(os.path.exists(be_dockerfile), "backend/Dockerfile must exist")
        with open(be_dockerfile, "r", encoding="utf-8") as f:
            be_content = f.read()
        self.assertIn("ENV SERVICE_VERSION=3.3.2", be_content)
        self.assertIn("ENV VERIFICATION_MARKER=v3.3.2-verified", be_content)

    def test_02_cloudbuild_v3_configuration(self):
        """Verifies cloudbuild-v3.yaml pipeline steps, tests, and substitutions."""
        cb_path = os.path.join(REPO_ROOT, "cloudbuild-v3.yaml")
        docs = load_yaml_documents(cb_path)
        self.assertEqual(len(docs), 1)
        cb = docs[0]
        self.assertIsInstance(cb, dict, "cloudbuild-v3.yaml root must be a mapping")

        steps = cb.get("steps", [])
        step_ids = [s.get("id") for s in steps]

        # Verify key steps exist
        self.assertIn("go-backend-tests", step_ids)
        self.assertIn("build-container-image", step_ids)
        self.assertIn("push-to-artifact-registry", step_ids)
        self.assertIn("apply-cloud-deploy-pipeline", step_ids)
        self.assertIn("create-cloud-deploy-release", step_ids)

        # Check Dockerfile.v3 reference in build step
        build_step = next(s for s in steps if s.get("id") == "build-container-image")
        self.assertIn("Dockerfile.v3", build_step.get("args", []))

        # Check substitutions
        substitutions = cb.get("substitutions", {})
        self.assertEqual(substitutions.get("_SERVICE_NAME"), "conductor-v3")
        self.assertEqual(substitutions.get("_DELIVERY_PIPELINE_NAME"), "conductor-v3-pipeline")
        self.assertEqual(substitutions.get("_REGION"), "us-central1")

        # Check options for SLSA Level 3 build provenance
        self.assertIn("options", cb, "cloudbuild-v3.yaml must declare 'options'")
        options = cb.get("options")
        self.assertIsInstance(options, dict, "cloudbuild-v3.yaml 'options' must be a mapping")
        self.assertEqual(
            options.get("requestedVerifyOption"),
            "VERIFIED",
            "cloudbuild-v3.yaml must declare requestedVerifyOption: 'VERIFIED' for SLSA Level 3 provenance",
        )

        # Check top-level images stanza for SLSA Level 3 build provenance
        self.assertIn("images", cb, "cloudbuild-v3.yaml must declare 'images:' for SLSA Level 3 provenance")
        images = cb.get("images")
        self.assertIsInstance(images, list, "cloudbuild-v3.yaml 'images:' must be a list")
        self.assertGreater(len(images), 0, "cloudbuild-v3.yaml 'images:' list cannot be empty")
        self.assertTrue(
            all(isinstance(img, str) and img.strip() for img in images),
            "cloudbuild-v3.yaml 'images:' items must be non-empty strings",
        )
        self.assertTrue(
            any("${_COMMIT_SHA}" in img and "${_SERVICE_NAME}" in img for img in images),
            "cloudbuild-v3.yaml 'images:' must declare immutable image tag referencing ${_COMMIT_SHA} and ${_SERVICE_NAME}",
        )


    def test_03_clouddeploy_v3_pipeline_and_targets(self):
        """Verifies clouddeploy-v3.yaml stages, targets, and canary deployment strategy."""
        cd_path = os.path.join(REPO_ROOT, "clouddeploy-v3.yaml")
        docs = load_yaml_documents(cd_path)
        self.assertGreaterEqual(len(docs), 4)

        pipeline_doc = next((d for d in docs if d.get("kind") == "DeliveryPipeline"), None)
        self.assertIsNotNone(pipeline_doc)
        self.assertEqual(pipeline_doc["metadata"]["name"], "conductor-v3-pipeline")

        # Verify stages: dev -> staging -> prod
        stages = pipeline_doc["serialPipeline"]["stages"]
        stage_ids = [s["targetId"] for s in stages]
        self.assertEqual(stage_ids, ["dev", "staging", "prod"])

        # Verify strategy.standard.verify on dev and staging
        dev_stage = next(s for s in stages if s["targetId"] == "dev")
        self.assertTrue(dev_stage.get("strategy", {}).get("standard", {}).get("verify"), "Dev stage must enable standard verification")

        staging_stage = next(s for s in stages if s["targetId"] == "staging")
        self.assertTrue(staging_stage.get("strategy", {}).get("standard", {}).get("verify"), "Staging stage must enable standard verification")

        # Verify prod stage canary
        prod_stage = next(s for s in stages if s["targetId"] == "prod")
        self.assertIn("canary", prod_stage.get("strategy", {}))
        canary = prod_stage["strategy"]["canary"]
        self.assertTrue(canary.get("runtimeConfig", {}).get("cloudRun", {}).get("automaticTrafficControl"))
        self.assertEqual(canary.get("canaryDeployment", {}).get("percentages"), [25, 50])
        self.assertTrue(canary.get("canaryDeployment", {}).get("verify"), "Canary deployment must enable verification")

        # Verify targets and executionConfigs
        targets = [d for d in docs if d.get("kind") == "Target"]
        target_names = [t["metadata"]["name"] for t in targets]
        self.assertIn("dev", target_names)
        self.assertIn("staging", target_names)
        self.assertIn("prod", target_names)

        required_params = {
            "name",
            "labels.env",
            "maxScale",
            "apphub-display-name",
            "apphub-description",
            "ENVIRONMENT",
            "AGENT_DISPLAY_NAME",
        }
        expected_target_params = {
            "dev": {
                "name": "conductor-v3-dev",
                "labels.env": "dev",
                "maxScale": "5",
                "apphub-display-name": "The Conductor v3 - Development",
                "apphub-description": "Dev environment for Go serverless multi-agent platform",
                "ENVIRONMENT": "development",
                "AGENT_DISPLAY_NAME": "The Conductor v3 (Dev)",
            },
            "staging": {
                "name": "conductor-v3-staging",
                "labels.env": "staging",
                "maxScale": "10",
                "apphub-display-name": "The Conductor v3 - Staging",
                "apphub-description": "Staging pre-production environment for Go serverless multi-agent platform",
                "ENVIRONMENT": "staging",
                "AGENT_DISPLAY_NAME": "The Conductor v3 (Staging)",
            },
            "prod": {
                "name": "conductor-v3-prod",
                "labels.env": "prod",
                "maxScale": "20",
                "apphub-display-name": "The Conductor v3 - Production",
                "apphub-description": "Production environment for Go serverless multi-agent platform",
                "ENVIRONMENT": "production",
                "AGENT_DISPLAY_NAME": "The Conductor v3 (Production)",
            },
        }
        for target in targets:
            t_name = target["metadata"]["name"]
            exec_configs = target.get("executionConfigs", [])
            self.assertGreater(len(exec_configs), 0, f"Target {t_name} must have executionConfigs")
            usages = exec_configs[0].get("usages", [])
            self.assertTrue(
                {"RENDER", "DEPLOY", "VERIFY"}.issubset(set(usages)),
                f"Target {t_name} executionConfigs usages must contain RENDER, DEPLOY, and VERIFY, got {usages}",
            )
            self.assertEqual(
                exec_configs[0].get("workerPool"),
                "projects/riccardo-blog-test-v1/locations/us-central1/workerPools/cloudbuild-workerpool",
                f"Target {t_name} workerPool must be private worker pool",
            )
            self.assertEqual(
                exec_configs[0].get("executionTimeout"),
                "600s",
                f"Target {t_name} executionTimeout must be 600s",
            )
            self.assertIn(
                "deployParameters",
                target,
                f"Target {t_name} must declare deployParameters",
            )
            dp = target["deployParameters"]
            self.assertEqual(
                set(dp.keys()),
                required_params,
                f"Target {t_name} deployParameters keys must exactly match required parameter set",
            )
            for p, exp_val in expected_target_params[t_name].items():
                self.assertEqual(
                    dp.get(p),
                    exp_val,
                    f"Target {t_name} parameter '{p}' expected '{exp_val}', got '{dp.get(p)}'",
                )

        prod_target = next(t for t in targets if t["metadata"]["name"] == "prod")
        self.assertTrue(prod_target.get("requireApproval"))

        # Verify Automations
        automations = [d for d in docs if d.get("kind") == "Automation"]
        auto_names = [a["metadata"]["name"].split("/")[-1] for a in automations]
        self.assertIn("auto-promote-dev-to-staging", auto_names)
        self.assertIn("auto-advance-canary", auto_names)

        promote_auto = next(a for a in automations if "auto-promote-dev-to-staging" in a["metadata"]["name"])
        promote_rule = promote_auto.get("rules", [])[0].get("promoteReleaseRule", {})
        self.assertEqual(promote_rule.get("destinationTargetId"), "staging")

    def test_04_skaffold_v3_configuration(self):
        """Verifies skaffold-v3.yaml artifact definitions, profile manifests, and verify configuration."""
        sk_path = os.path.join(REPO_ROOT, "skaffold-v3.yaml")
        docs = load_yaml_documents(sk_path)
        self.assertEqual(len(docs), 1)
        sk = docs[0]

        self.assertEqual(sk.get("metadata", {}).get("name"), "conductor-v3")
        artifact = sk.get("build", {}).get("artifacts", [])[0]
        self.assertEqual(artifact.get("docker", {}).get("dockerfile"), "Dockerfile.v3")

        manifests = sk.get("manifests", {}).get("rawYaml", [])
        self.assertEqual(
            manifests,
            ["infra/cloudrun/service-v3.yaml.template"],
            "skaffold-v3.yaml rawYaml must reference parameterized template infra/cloudrun/service-v3.yaml.template without drift",
        )

        profiles = {p.get("name"): p for p in sk.get("profiles", [])}
        for env in ["dev", "staging", "prod"]:
            self.assertIn(env, profiles)
            self.assertEqual(
                profiles[env].get("manifests", {}).get("rawYaml", []),
                ["infra/cloudrun/service-v3.yaml.template"],
                f"Profile '{env}' in skaffold-v3.yaml must reference infra/cloudrun/service-v3.yaml.template without drift",
            )

        # Verify top-level verify configuration
        self.assertIn("verify", sk, "skaffold-v3.yaml must declare a top-level 'verify:' stanza")
        verify_entries = sk["verify"]
        self.assertIsInstance(verify_entries, list)
        self.assertGreater(len(verify_entries), 0)
        verify_container = verify_entries[0].get("container", {})
        self.assertEqual(verify_container.get("image"), "gcr.io/google.com/cloudsdktool/cloud-sdk:slim")
        command_str = " ".join(str(c) for c in verify_container.get("command", []))
        self.assertIn("verify_cloudrun_v3.sh", command_str)

        # Verify embedded base64 prober synchronization with canonical script
        import base64
        with open(sk_path, "r", encoding="utf-8") as f:
            sk_raw = f.read()
        b64_lines = []
        capturing = False
        for line in sk_raw.splitlines():
            if "PROBER_B64_EOF" in line:
                if capturing:
                    break
                else:
                    capturing = True
                    continue
            if capturing:
                b64_lines.append(line.strip())
        b64_data = "".join(b64_lines)
        decoded = base64.b64decode(b64_data).decode("utf-8")
        canonical_path = os.path.join(REPO_ROOT, "infra", "cloudrun", "verify_cloudrun_v3.sh")
        with open(canonical_path, "r", encoding="utf-8") as f:
            canonical = f.read()
        self.assertEqual(decoded, canonical, "Embedded base64 prober in skaffold-v3.yaml must match infra/cloudrun/verify_cloudrun_v3.sh byte-for-byte")

        # Verify customActions for agent evaluation
        self.assertIn("customActions", sk, "skaffold-v3.yaml must declare customActions")
        custom_actions = sk["customActions"]
        eval_action = next((a for a in custom_actions if a.get("name") == "verify-production-agent-eval"), None)
        self.assertIsNotNone(eval_action, "skaffold-v3.yaml must declare verify-production-agent-eval customAction")
        containers = eval_action.get("containers", [])
        self.assertGreater(len(containers), 0)
        eval_c = containers[0]
        self.assertEqual(eval_c.get("image"), "gcr.io/google.com/cloudsdktool/cloud-sdk:slim")
        eval_env = {e.get("name"): e.get("value") for e in eval_c.get("env", [])}
        self.assertEqual(eval_env.get("THRESHOLD_GROUNDEDNESS"), "0.80")
        self.assertEqual(eval_env.get("THRESHOLD_HALLUCINATION_RATE"), "0.05")
        self.assertEqual(eval_env.get("THRESHOLD_TOOL_CALL_ACCURACY"), "0.90")
        self.assertEqual(eval_env.get("VERTEX_EXPERIMENT_NAME"), "conductor-v3-prod-canary-eval")
        self.assertEqual(eval_env.get("MOCK_AGENT"), "true")

        eval_cmd = " ".join(str(c) for c in eval_c.get("command", []))
        self.assertIn("scripts/evaluate_production_agent.py", eval_cmd)
        self.assertIn("EXTRA_ARGS", eval_cmd)

        # Verify verify stanza for agent evaluation
        verify_stanzas = sk.get("verify", [])
        agent_verify = next((v for v in verify_stanzas if v.get("name") == "verify-agent-evaluation"), None)
        self.assertIsNotNone(agent_verify, "skaffold-v3.yaml must declare verify-agent-evaluation in verify: stanza")
        c_verify = agent_verify.get("container", {})
        self.assertEqual(c_verify.get("image"), "gcr.io/google.com/cloudsdktool/cloud-sdk:slim")
        verify_env = {e.get("name"): e.get("value") for e in c_verify.get("env", [])}
        self.assertEqual(verify_env.get("THRESHOLD_GROUNDEDNESS"), "0.80")
        self.assertEqual(verify_env.get("THRESHOLD_HALLUCINATION_RATE"), "0.05")
        self.assertEqual(verify_env.get("THRESHOLD_TOOL_CALL_ACCURACY"), "0.90")

    def test_05_cloudrun_service_v3_specification(self):
        """Verifies infra/cloudrun/service-v3.yaml and service-v3.yaml.template memory, CPU, health probes, and runtime."""
        for svc_file in ["service-v3.yaml", "service-v3.yaml.template"]:
            service_path = os.path.join(REPO_ROOT, "infra", "cloudrun", svc_file)
            docs = load_yaml_documents(service_path)
            self.assertEqual(len(docs), 1, f"{svc_file} must contain 1 document")
            svc = docs[0]

            labels = svc.get("metadata", {}).get("labels", {})
            self.assertEqual(labels.get("runtime"), "go-cloud-run", f"{svc_file} runtime label mismatch")

            template = svc.get("spec", {}).get("template", {})
            annotations = template.get("metadata", {}).get("annotations", {})
            self.assertEqual(annotations.get("run.googleapis.com/cpu-throttling"), "false", f"{svc_file} cpu-throttling mismatch")
            self.assertEqual(annotations.get("run.googleapis.com/startup-cpu-boost"), "true", f"{svc_file} startup-cpu-boost mismatch")

            container = template.get("spec", {}).get("containers", [])[0]
            resources = container.get("resources", {}).get("limits", {})
            self.assertEqual(resources.get("cpu"), "1000m", f"{svc_file} CPU limit mismatch")
            self.assertEqual(resources.get("memory"), "512Mi", f"{svc_file} memory limit mismatch")

            # Concurrency and timeout
            template_spec = template.get("spec", {})
            self.assertEqual(template_spec.get("containerConcurrency"), 100, f"{svc_file} containerConcurrency mismatch")
            self.assertEqual(template_spec.get("timeoutSeconds"), 3600, f"{svc_file} timeoutSeconds mismatch")
            self.assertEqual(
                template_spec.get("serviceAccountName"),
                "conductor-agent@riccardo-blog-test-v1.iam.gserviceaccount.com",
                f"{svc_file} serviceAccountName mismatch"
            )

            # Cloud SQL socket annotation
            self.assertEqual(
                annotations.get("run.googleapis.com/cloudsql-instances"),
                "riccardo-blog-test-v1:us-central1:genai-rag-db-859a1005",
                f"{svc_file} Cloud SQL instance annotation mismatch"
            )

            # Probes detailed configuration
            startup_probe = container.get("startupProbe", {})
            self.assertEqual(startup_probe.get("httpGet", {}).get("path"), "/health", f"{svc_file} startup probe path mismatch")
            self.assertEqual(startup_probe.get("httpGet", {}).get("port"), 8080, f"{svc_file} startup probe port mismatch")
            self.assertEqual(startup_probe.get("initialDelaySeconds"), 2, f"{svc_file} startup probe initialDelaySeconds mismatch")
            self.assertEqual(startup_probe.get("periodSeconds"), 5, f"{svc_file} startup probe periodSeconds mismatch")
            self.assertEqual(startup_probe.get("failureThreshold"), 12, f"{svc_file} startup probe failureThreshold mismatch")
            self.assertEqual(startup_probe.get("timeoutSeconds"), 3, f"{svc_file} startup probe timeoutSeconds mismatch")

            liveness_probe = container.get("livenessProbe", {})
            self.assertEqual(liveness_probe.get("httpGet", {}).get("path"), "/health", f"{svc_file} liveness probe path mismatch")
            self.assertEqual(liveness_probe.get("httpGet", {}).get("port"), 8080, f"{svc_file} liveness probe port mismatch")
            self.assertEqual(liveness_probe.get("initialDelaySeconds"), 5, f"{svc_file} liveness probe initialDelaySeconds mismatch")
            self.assertEqual(liveness_probe.get("periodSeconds"), 15, f"{svc_file} liveness probe periodSeconds mismatch")
            self.assertEqual(liveness_probe.get("failureThreshold"), 3, f"{svc_file} liveness probe failureThreshold mismatch")
            self.assertEqual(liveness_probe.get("timeoutSeconds"), 3, f"{svc_file} liveness probe timeoutSeconds mismatch")

        # Verify Declarative Version Metadata across all Backend Cloud Run manifests (template, dev, staging, prod)
        for svc_file in ["service-v3.yaml.template", "service-v3.yaml", "service-v3-staging.yaml", "service-v3-dev.yaml"]:
            p = os.path.join(REPO_ROOT, "infra", "cloudrun", svc_file)
            self.assertTrue(os.path.exists(p), f"{svc_file} must exist")
            manifest_docs = load_yaml_documents(p)
            c = manifest_docs[0].get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])[0]
            envs = {e.get("name"): e.get("value") for e in c.get("env", []) if "value" in e}
            self.assertEqual(envs.get("SERVICE_VERSION"), "3.3.2", f"SERVICE_VERSION in {svc_file} must be 3.3.2")
            self.assertEqual(envs.get("VERIFICATION_MARKER"), "v3.3.2-verified", f"VERIFICATION_MARKER in {svc_file} must be v3.3.2-verified")

        # Verify Declarative Version Metadata across all Frontend Cloud Run manifests (dev, staging, prod)
        for fe_file in ["service-frontend-prod.yaml", "service-frontend-staging.yaml", "service-frontend-dev.yaml"]:
            fe_service_path = os.path.join(REPO_ROOT, "infra", "cloudrun", fe_file)
            self.assertTrue(os.path.exists(fe_service_path), f"{fe_file} must exist")
            fe_docs = load_yaml_documents(fe_service_path)
            fe_container = fe_docs[0].get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])[0]
            fe_envs = {e.get("name"): e.get("value") for e in fe_container.get("env", []) if "value" in e}
            self.assertEqual(fe_envs.get("SERVICE_VERSION"), "3.3.1", f"SERVICE_VERSION in {fe_file} must be 3.3.1")
            self.assertEqual(fe_envs.get("VERIFICATION_MARKER"), "v3.3.1-verified", f"VERIFICATION_MARKER in {fe_file} must be v3.3.1-verified")

    def test_06_cloudbuild_v3_trigger_specification(self):
        """Verifies infra/triggers/conductor-v3-ci-trigger.yaml schema, Developer Connect binding, and filters."""
        trigger_path = os.path.join(REPO_ROOT, "infra", "triggers", "conductor-v3-ci-trigger.yaml")
        self.assertTrue(os.path.exists(trigger_path), "conductor-v3-ci-trigger.yaml must exist under infra/triggers/")

        docs = load_yaml_documents(trigger_path)
        self.assertEqual(len(docs), 1)
        trigger = docs[0]

        self.assertEqual(trigger.get("name"), "conductor-v3-ci-trigger")
        self.assertEqual(trigger.get("filename"), "cloudbuild-v3.yaml")

        dc_config = trigger.get("developerConnectEventConfig", {})
        expected_repo = (
            "projects/riccardo-blog-test-v1/locations/us-east4/connections/github-testing-02/"
            "gitRepositoryLinks/nateaveryg-analyst-response-conductor"
        )
        self.assertEqual(dc_config.get("gitRepositoryLink"), expected_repo)
        self.assertEqual(dc_config.get("push", {}).get("branch"), "^main$")

        included = trigger.get("includedFiles", [])
        expected_included = [
            "backend/**",
            "infra/**",
            "Dockerfile.v3",
            "cloudbuild-v3.yaml",
            "clouddeploy-v3.yaml",
            "skaffold-v3.yaml",
        ]
        self.assertEqual(set(included), set(expected_included))

        subs = trigger.get("substitutions", {})
        self.assertEqual(subs.get("_REGION"), "us-central1")
        self.assertEqual(subs.get("_REPO_NAME"), "conductor-repo")
        self.assertEqual(subs.get("_SERVICE_NAME"), "conductor-v3")
        self.assertEqual(subs.get("_DELIVERY_PIPELINE_NAME"), "conductor-v3-pipeline")

    def test_07_cloudbuild_v3_trigger_adverse_changeset_filtering(self):
        """Adversarially validates that commits touching only non-pipeline files are suppressed."""
        import fnmatch
        trigger_path = os.path.join(REPO_ROOT, "infra", "triggers", "conductor-v3-ci-trigger.yaml")
        trigger = load_yaml_documents(trigger_path)[0]
        included_globs = trigger.get("includedFiles", [])

        def normalize_git_path(p: str) -> str:
            if not isinstance(p, str):
                return ""
            norm = p.strip()
            while norm.startswith("./") or norm.startswith("/"):
                if norm.startswith("./"):
                    norm = norm[2:]
                elif norm.startswith("/"):
                    norm = norm[1:]
            return norm

        def matches_glob(path: str, glob_pattern: str) -> bool:
            norm_path = normalize_git_path(path)
            if not norm_path:
                return False
            if glob_pattern.endswith("/**"):
                prefix = glob_pattern[:-3]
                return norm_path.startswith(prefix + "/")
            return fnmatch.fnmatch(norm_path, glob_pattern)

        def should_trigger(changeset: list) -> bool:
            if not changeset:
                return False
            return any(any(matches_glob(f, g) for g in included_globs) for f in changeset)

        # Adverse non-pipeline changesets (MUST NOT fire trigger)
        doc_changes = ["README.md", "docs/architecture.md", "docs/workflow_diagrams.jpg"]
        self.assertFalse(should_trigger(doc_changes), "Documentation-only commits must be suppressed")

        fe_changes = ["frontend/lib/main.dart", "frontend/pubspec.yaml"]
        self.assertFalse(should_trigger(fe_changes), "Frontend-only commits must be suppressed")

        ae_changes = ["app/agent_engine_go/agent/conductor_agent.go", "cloudbuild-agent-engine.yaml"]
        self.assertFalse(should_trigger(ae_changes), "Agent Engine commits must be suppressed")

        near_misses = ["backend_extra/foo.go", "Dockerfile.v3.bak", "cloudbuild-v3.yaml.old", "infra_old/main.tf"]
        self.assertFalse(should_trigger(near_misses), "Near-miss files must be suppressed")

        # Boundary prefix tests (bare root files matching directory prefixes must not match)
        bare_files = ["backend", "infra"]
        self.assertFalse(should_trigger(bare_files), "Bare root files must not match directory globs")

        # Dotfile and null/invalid changesets
        self.assertFalse(should_trigger([".gitignore", ".github/workflows/ci.yaml"]), "Dotfiles must be suppressed")
        self.assertFalse(should_trigger([None, "", "   ", 789]), "Invalid entries must be suppressed")
        self.assertFalse(should_trigger([]), "Empty changeset must be suppressed")

        # Mixed and pipeline changesets (MUST fire trigger)
        self.assertTrue(should_trigger(["README.md", "backend/cmd/server/main.go"]))
        self.assertTrue(should_trigger(["docs/index.md", "cloudbuild-v3.yaml"]))
        self.assertTrue(should_trigger(["clouddeploy-v3.yaml"]))
        self.assertTrue(should_trigger(["skaffold-v3.yaml"]))
        self.assertTrue(should_trigger(["Dockerfile.v3"]))
        self.assertTrue(should_trigger(["./backend/internal/agent/agent.go"]), "Relative path './' must trigger")
        self.assertTrue(should_trigger(["./Dockerfile.v3"]), "Relative path './' must trigger")


if __name__ == "__main__":
    unittest.main()

