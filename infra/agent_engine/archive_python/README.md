# Archived Python deployer assets

This directory preserves deprecated Python deployer assets for historical reference.

## Overview

The scripts in this directory implemented the legacy Python `cloudpickle` deployment pattern.
Vertex AI Reasoning Engine originally required serialization of Python class instances.
These assets packaged agent code into Cloud Storage before microVM initialization.

## Archived assets

This archive preserves the following legacy components:
* `deploy_agent_engine.py` – Orchestrated legacy serialization and remote microVM deployments.
* `render_agent_engine.py` – Generated deployment parameters for Cloud Deploy releases.
* `verify_agent_engine.py` – Probed live reasoning engine endpoints after deployment.
* `promote_and_verify_all.py` – Coordinated multi-tier stage progression across environments.
* `Dockerfile.runner` – Built the runtime container image for deployment verification.
* `cloudbuild-runner.yaml` – Executed container builds for the legacy runner.
* `requirements.txt` – Configured Python dependencies for legacy microVM package builds.
* `results.json` – Recorded deployment execution output from legacy reasoning engine runs.

## Current architecture

The project now uses the Go Agent Development Kit (ADK).
All active Agent Engine workflows run through compiled Go binaries.
Active deployment manifests reside in the primary `infra/agent_engine/` directory.
